from rest_framework import serializers

from exercises.models import Exercise, ExerciseType


class ExerciseTypeSerializer(serializers.ModelSerializer):
    """Сериализатор объектов класса ExerciseType."""

    class Meta:
        model = ExerciseType
        fields = ('id', 'name', 'description')


class ExerciseSerializer(serializers.ModelSerializer):
    """Сериализатор объектов класса Exercise."""

    type = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Exercise
        fields = (
            'id',
            'title',
            'description',
            'type',
            'difficulty',
            'config',
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
