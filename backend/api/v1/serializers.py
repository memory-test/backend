from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from authentication import services
from authentication.constants import CODE_LENGTH
from authentication.models import EmailCode
from exercises.models import Exercise
from users.constants import EMAIL_LENGTH, NAME_LENGTH
from users.models import User


class ExerciseSerializer(serializers.ModelSerializer):
    """Сериализатор объектов класса Exercise."""

    class Meta:
        model = Exercise
        fields = (
            'id',
            'title',
            'description',
            'type',
            'difficulty',
            'is_active',
            'created_at',
        )


class ExerciseSessionSerializer(serializers.Serializer):
    """Валидирует данные, которые присылвает фронтенд."""

    started_at = serializers.DateTimeField(required=True)
    finished_at = serializers.DateTimeField(required=True)
    duration_seconds = serializers.IntegerField(required=True)
    # пока это поле рассчитано, что за одно упражнение пользователь
    # отправляет один финальный результат, в дальнейшем напишем сериализатор.
    answer_data = serializers.JSONField(required=True)

    def validate(self, attrs):
        """Проверяем согласованность даты начала и окончания задания."""
        if attrs['started_at'] >= attrs['finished_at']:
            raise serializers.ValidationError(
                {
                    'finished_at': (
                        'Время окончания должно быть позже времени начала.'
                    )
                }
            )
        return attrs

    def validate_duration_seconds(self, value):
        if value < 0:
            raise serializers.ValidationError(
                'Продолжительность не может быть отрицательной.'
            )
        return value


PASSWORD_STYLE = {'input_type': 'password'}

VERIFY_PURPOSES = (
    (services.REGISTRATION, 'Регистрация'),
    (services.LOGIN, 'Вход'),
)


class RegisterSerializer(serializers.Serializer):
    """Регистрация: email + имя, пароль опционален (упрощённая регистрация)."""

    email = serializers.EmailField(max_length=EMAIL_LENGTH)
    name = serializers.CharField(max_length=NAME_LENGTH)
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=False,
        trim_whitespace=False,
        style=PASSWORD_STYLE,
    )
    birth_date = serializers.DateField(required=False)

    def validate_email(self, value):
        """Запрещает повторную регистрацию по уже занятому email."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'Пользователь с таким email уже существует.'
            )
        return value

    def validate_password(self, value):
        """Прогоняет пароль через настроенные AUTH_PASSWORD_VALIDATORS."""
        if value:
            try:
                validate_password(value)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(list(exc.messages))
        return value


class CodeRequestSerializer(serializers.Serializer):
    """Запрос кода подтверждения."""

    email = serializers.EmailField(max_length=EMAIL_LENGTH)
    purpose = serializers.ChoiceField(choices=EmailCode.Purpose.choices)


class CodeVerifySerializer(serializers.Serializer):
    """Подтверждение кода (регистрация / вход) — возвращает JWT."""

    email = serializers.EmailField(max_length=EMAIL_LENGTH)
    code = serializers.CharField(
        max_length=CODE_LENGTH, min_length=1, trim_whitespace=True
    )
    purpose = serializers.ChoiceField(choices=VERIFY_PURPOSES)


class PasswordResetSerializer(serializers.Serializer):
    """Запрос сброса пароля."""

    email = serializers.EmailField(max_length=EMAIL_LENGTH)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Сброс пароля по коду из email."""

    email = serializers.EmailField(max_length=EMAIL_LENGTH)
    code = serializers.CharField(
        max_length=CODE_LENGTH, min_length=1, trim_whitespace=True
    )
    new_password = serializers.CharField(
        write_only=True,
        allow_blank=False,
        trim_whitespace=False,
        style=PASSWORD_STYLE,
    )

    def validate_new_password(self, value):
        """Прогоняет новый пароль через AUTH_PASSWORD_VALIDATORS."""
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value


class UserSerializer(serializers.ModelSerializer):
    """Профиль пользователя."""

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
