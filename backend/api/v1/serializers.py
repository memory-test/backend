from rest_framework import serializers

from authentication import services
from authentication.constants import CODE_LENGTH
from exercises.models import Exercise
from users.constants import EMAIL_LENGTH


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


VERIFY_PURPOSES = (
    (services.REGISTRATION, 'Регистрация'),
    (services.LOGIN, 'Вход'),
)


class LoginCodeRequestSerializer(serializers.Serializer):
    """Запрос кода для входа (регистрация и сброс — эндпоинты djoser)."""

    email = serializers.EmailField(max_length=EMAIL_LENGTH)


class CodeVerifySerializer(serializers.Serializer):
    """Подтверждение кода (регистрация / вход) — возвращает JWT."""

    email = serializers.EmailField(max_length=EMAIL_LENGTH)
    code = serializers.CharField(
        max_length=CODE_LENGTH, min_length=1, trim_whitespace=True
    )
    purpose = serializers.ChoiceField(choices=VERIFY_PURPOSES)
