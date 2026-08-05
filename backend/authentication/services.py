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


def generate_code() -> str:
    """Возвращает случайный цифровой код заданной длины."""
    max_value = 10**constants.CODE_LEN
    return str(secrets.randbelow(max_value)).zfill(constants.CODE_LEN)


def register_user(email, name, password=None, birth_date=None):
    """Создаёт неактивного пользователя и отправляет код подтверждения."""
    user = User(
        email=email,
        name=name,
        birth_date=birth_date,
        is_active=False,
    )
    if password:
        user.set_password(password)
    else:
        user.set_unusable_password()
    user.save()
    create_code(email, REGISTRATION)
    return user


def request_code(email, purpose):
    """Отправляет код, если для (email, purpose) есть основание.

    Для несуществующих/неактивных пользователей молча ничего не делает
    (анти-enumeration). Поднимает CooldownError/RateLimitError при лимитах.
    """
    user = User.objects.filter(email=email).first()
    if purpose == REGISTRATION:
        # Повторная отправка только для незавершённой регистрации.
        if user is None or user.is_active:
            return
    elif user is None or not user.is_active:
        return
    create_code(email, purpose)


def create_code(email, purpose):
    """Создаёт новый код для (email, purpose) и отправляет его на почту.

    Аннулирует предыдущие неиспользованные коды для этой пары.
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
    code = generate_code()
    EmailCode.objects.create(
        email=email,
        code_hash=make_password(code),
        purpose=purpose,
        expires_at=now + timedelta(minutes=constants.CODE_TTL_MINUTES),
    )
    send_code_email(email, code, purpose)


def send_code_email(email, code, purpose):
    """Отправляет код подтверждения на email (тема/текст по назначению)."""
    subjects = {
        REGISTRATION: 'Подтверждение регистрации',
        LOGIN: 'Код для входа',
        PASSWORD_RESET: 'Восстановление пароля',
    }
    templates = {
        REGISTRATION: 'Ваш код подтверждения регистрации: {code}',
        LOGIN: 'Ваш код для входа: {code}',
        PASSWORD_RESET: 'Ваш код для сброса пароля: {code}',
    }
    send_mail(
        subject=subjects[purpose],
        message=templates[purpose].format(code=code),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


def verify_code(email, code, purpose):
    """Проверяет код и возвращает объект EmailCode при успехе.

    Поднимает CodeVerificationError при любой ошибке проверки.
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
    return instance


def reset_password(email, code, new_password):
    """Проверяет код сброса и устанавливает новый пароль."""
    verify_code(email, code, PASSWORD_RESET)
    user = User.objects.get(email=email)
    user.set_password(new_password)
    user.save()
    blacklist_user_tokens(user)


def blacklist_user_tokens(user):
    """Блокирует все ранее выданные токены пользователя."""
    # Локальный импорт, чтобы не связывать слой сервисов с JWT-моделями.
    from rest_framework_simplejwt.token_blacklist.models import (
        BlacklistedToken,
        OutstandingToken,
    )

    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)
