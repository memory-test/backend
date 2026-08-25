"""Переопределения djoser под одноразовые коды из писем.

djoser закрывает стандартные флоу (регистрация, профиль, сброс пароля,
JWT). Всё, что связано с кодами подтверждения, живёт в сервисах
authentication.services и подключается здесь через штатные точки
расширения — DJOSER['SERIALIZERS'] и DJOSER['EMAIL'].
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from djoser.email import ActivationEmail, PasswordResetEmail
from djoser.serializers import UserCreateMixin
from rest_framework import serializers

from users.constants import EMAIL_LENGTH
from users.models import User

from . import constants, services

PASSWORD_STYLE = {'input_type': 'password'}


class CodeUserSerializer(serializers.ModelSerializer):
    """Профиль пользователя для /users/me/ (все поля только для чтения)."""

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'name',
            'birth_date',
            'current_difficulty',
            'role',
            'is_active',
            'date_joined',
        )
        read_only_fields = fields


class CodeUserCreateSerializer(UserCreateMixin, serializers.ModelSerializer):
    """Регистрация: email + имя, пароль опционален (упрощённая регистрация).

    UserCreateMixin.perform_create при включённом SEND_ACTIVATION_EMAIL
    создаёт неактивного пользователя; без пароля вход по паролю
    невозможен (set_password(None) делает пароль непригодным).
    """

    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        trim_whitespace=False,
        style=PASSWORD_STYLE,
    )

    class Meta:
        model = User
        fields = ('id', 'email', 'name', 'birth_date', 'password')

    def validate_password(self, value):
        """Прогоняет пароль через AUTH_PASSWORD_VALIDATORS."""
        if value:
            try:
                validate_password(value)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(list(exc.messages))
        return value


class CodeActivationSerializer(serializers.Serializer):
    """Активация аккаунта по коду: {email, code}."""

    user: User

    email = serializers.EmailField(max_length=EMAIL_LENGTH)
    code = serializers.CharField(
        max_length=constants.CODE_LENGTH, min_length=1, trim_whitespace=True
    )

    def validate(self, attrs):
        """Проверяет код активации и поднимает self.user."""
        try:
            services.consume_code(
                attrs['email'], attrs['code'], services.REGISTRATION
            )
        except services.CodeVerificationError as exc:
            raise serializers.ValidationError({'detail': str(exc)})
        user = User.objects.filter(email=attrs['email']).first()
        if user is None:
            raise serializers.ValidationError(
                {'detail': 'Пользователь не найден.'}
            )
        self.user = user
        return attrs


class CodePasswordResetConfirmSerializer(serializers.Serializer):
    """Сброс пароля по коду: {email, code, new_password}.

    new_password намеренно не write_only: вью djoser читает значение
    из serializer.data уже после валидации.
    """

    user: User

    email = serializers.EmailField(max_length=EMAIL_LENGTH)
    code = serializers.CharField(
        max_length=constants.CODE_LENGTH, min_length=1, trim_whitespace=True
    )
    new_password = serializers.CharField(
        allow_blank=False,
        trim_whitespace=False,
        style=PASSWORD_STYLE,
    )

    def validate(self, attrs):
        """Проверяет пароль, затем код; поднимает self.user.

        Слабый пароль проверяется до расходования кода, чтобы ошибка
        не «сжигала» его. Код проверяется раньше факта существования
        пользователя в ответе — анти-enumeration.
        """
        try:
            validate_password(attrs['new_password'])
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {'new_password': list(exc.messages)}
            )
        try:
            services.consume_code(
                attrs['email'], attrs['code'], services.PASSWORD_RESET
            )
        except services.CodeVerificationError as exc:
            raise serializers.ValidationError({'detail': str(exc)})
        user = User.objects.filter(email=attrs['email']).first()
        if user is None:
            raise serializers.ValidationError(
                {'detail': 'Пользователь не найден.'}
            )
        services.blacklist_user_tokens(user)
        self.user = user
        return attrs


class _CodeEmailMixin:
    """Отправляет код подтверждения вместо письма со ссылкой.

    Кулдаун и лимит отправок гасятся: djoser-эндпоинты отвечают единым
    204, поэтому повторный код просто не отправляется.
    """

    purpose: str = ''

    def send(self, to, fail_silently=False, **kwargs):
        user = self.context.get('user')
        try:
            services.issue_code(user.email, self.purpose)
        except (services.CooldownError, services.RateLimitError):
            pass


class CodeActivationEmail(_CodeEmailMixin, ActivationEmail):
    """Письмо с кодом активации при регистрации/пересылке."""

    purpose = services.REGISTRATION


class CodePasswordResetEmail(_CodeEmailMixin, PasswordResetEmail):
    """Письмо с кодом сброса пароля."""

    purpose = services.PASSWORD_RESET
