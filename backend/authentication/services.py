"""Сервисный слой авторизации.

Регистрация, вход по паролю и одноразовому коду, восстановление пароля.
Хранение и проверка одноразовых кодов (модель EmailCode), кулдаун и
лимиты отправок, выдача и отзыв JWT.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.utils import timezone

from users.models import User

from . import constants
from .models import EmailCode

REGISTRATION = EmailCode.Purpose.REGISTRATION.value
LOGIN = EmailCode.Purpose.LOGIN.value
PASSWORD_RESET = EmailCode.Purpose.PASSWORD_RESET.value


class CodeError(Exception):
    """Базовая ошибка работы с кодами подтверждения."""


class CooldownError(CodeError):
    """Код запрошен слишком быстро (действует кулдаун)."""


class RateLimitError(CodeError):
    """Превышен лимит запросов кода за период."""


class CodeVerificationError(CodeError):
    """Код недействителен, просрочен или лимит попыток исчерпан."""


_SUBJECTS = {
    REGISTRATION: 'Подтверждение регистрации',
    LOGIN: 'Код для входа',
    PASSWORD_RESET: 'Восстановление пароля',
}
_TEMPLATES = {
    REGISTRATION: 'Ваш код подтверждения регистрации: {code}',
    LOGIN: 'Ваш код для входа: {code}',
    PASSWORD_RESET: 'Ваш код для сброса пароля: {code}',
}


def _generate_code() -> str:
    """Возвращает случайный цифровой код заданной длины."""
    max_value = 10**constants.CODE_LEN
    return str(secrets.randbelow(max_value)).zfill(constants.CODE_LEN)


def _send_code_email(email: str, code: str, purpose: str) -> None:
    """Отправляет письмо с кодом (тема/текст зависят от purpose)."""
    send_mail(
        subject=_SUBJECTS[purpose],
        message=_TEMPLATES[purpose].format(code=code),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


def _issue_code(email: str, purpose: str) -> None:
    """Создаёт новый код для (email, purpose) и отправляет его на почту.

    Общая точка входа для всех флоу: проверяет кулдаун и лимит отправок,
    аннулирует предыдущие неиспользованные коды, создаёт новый и шлёт email.
    Поднимает CooldownError/RateLimitError при превышении лимитов.
    """
    now = timezone.now()
    active_codes = EmailCode.objects.filter(
        email=email, purpose=purpose, is_used=False
    )

    last = active_codes.order_by('-created_at').first()
    cooldown = timedelta(seconds=constants.CODE_COOLDOWN_SECONDS)
    if last is not None and last.created_at + cooldown > now:
        raise CooldownError('Код уже отправлен. Запросите новый через минуту.')

    sent_last_hour = EmailCode.objects.filter(
        email=email,
        purpose=purpose,
        created_at__gte=now - timedelta(hours=1),
    ).count()
    if sent_last_hour >= constants.MAX_CODES_PER_HOUR:
        raise RateLimitError('Слишком много запросов кода. Попробуйте позже.')

    active_codes.delete()
    code = _generate_code()
    EmailCode.objects.create(
        email=email,
        code_hash=make_password(code),
        purpose=purpose,
        expires_at=now + timedelta(minutes=constants.CODE_TTL_MINUTES),
    )
    _send_code_email(email, code, purpose)


def _consume_code(email: str, code: str, purpose: str) -> None:
    """Проверяет код для (email, purpose) и помечает его использованным.

    Поднимает CodeVerificationError при любой ошибке проверки
    (не найден, просрочен, лимит попыток, неверный код).
    """
    instance = (
        EmailCode.objects.filter(email=email, purpose=purpose, is_used=False)
        .order_by('-created_at')
        .first()
    )
    if instance is None:
        raise CodeVerificationError('Код не найден или уже использован.')
    if instance.expires_at <= timezone.now():
        instance.is_used = True
        instance.save(update_fields=['is_used'])
        raise CodeVerificationError('Срок действия кода истёк.')
    if instance.attempts >= constants.MAX_VERIFY_ATTEMPTS:
        instance.is_used = True
        instance.save(update_fields=['is_used', 'attempts'])
        raise CodeVerificationError(
            'Превышено число попыток. Запросите новый код.'
        )
    if not check_password(code, instance.code_hash):
        instance.attempts += 1
        instance.save(update_fields=['attempts'])
        raise CodeVerificationError('Неверный код.')
    instance.is_used = True
    instance.save(update_fields=['is_used'])


def _issue_tokens(user: User) -> dict:
    """Возвращает пару JWT (access, refresh) для пользователя."""
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


def _blacklist_user_tokens(user: User) -> None:
    """Блокирует все ранее выданные токены пользователя."""
    from rest_framework_simplejwt.token_blacklist.models import (
        BlacklistedToken,
        OutstandingToken,
    )

    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


def start_registration(
    email: str, name: str, password: str | None = None, birth_date=None
) -> User:
    """Создаёт неактивного пользователя и отправляет код подтверждения.

    Если password не передан — регистрация упрощённая (пароль не задаётся,
    вход в дальнейшем только по коду).
    """
    user = User(email=email, name=name, birth_date=birth_date, is_active=False)
    if password:
        user.set_password(password)
    else:
        user.set_unusable_password()
    user.save()
    _issue_code(email, REGISTRATION)
    return user


def resend_registration_code(email: str) -> None:
    """Повторно отправляет код регистрации, если она не завершена.

    Анти-enumeration: для несуществующего/уже активного пользователя
    молча ничего не делает.
    """
    user = User.objects.filter(email=email).first()
    if user is None or user.is_active:
        return
    _issue_code(email, REGISTRATION)


def confirm_registration(email: str, code: str) -> tuple[User, dict]:
    """Подтверждает код регистрации, активирует пользователя, выдаёт JWT."""
    _consume_code(email, code, REGISTRATION)
    user = User.objects.get(email=email)
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=['is_active'])
    return user, _issue_tokens(user)


def request_login_code(email: str) -> None:
    """Отправляет код для входа активному пользователю.

    Анти-enumeration: для несуществующего/неактивного пользователя
    молча ничего не делает.
    """
    user = User.objects.filter(email=email).first()
    if user is None or not user.is_active:
        return
    _issue_code(email, LOGIN)


def login_with_code(email: str, code: str) -> tuple[User, dict]:
    """Подтверждает код входа и выдаёт JWT."""
    _consume_code(email, code, LOGIN)
    user = User.objects.get(email=email)
    return user, _issue_tokens(user)


def start_password_reset(email: str) -> None:
    """Отправляет код сброса пароля активному пользователю.

    Анти-enumeration: для несуществующего/неактивного пользователя
    молча ничего не делает.
    """
    user = User.objects.filter(email=email).first()
    if user is None or not user.is_active:
        return
    _issue_code(email, PASSWORD_RESET)


def confirm_password_reset(email: str, code: str, new_password: str) -> None:
    """Проверяет код сброса, ставит новый пароль, блокирует старые токены."""
    _consume_code(email, code, PASSWORD_RESET)
    user = User.objects.get(email=email)
    user.set_password(new_password)
    user.save()
    _blacklist_user_tokens(user)
