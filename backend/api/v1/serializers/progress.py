from rest_framework import serializers
from progress.models import ExerciseSession, UserAnswer


# По названию класса это выглядит, как сериализатор модели Заданий,
# хотя это не так. Скорее всего это для сессии упражения.
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


class HistoryListSerializer(serializers.ModelSerializer):
    """
    Список истории прохождения упражнений (краткая информация).
    GET /api/progress/history/
    """
    exercise_title = serializers.CharField(
        source='exercise.title',
        read_only=True
    )
    exercise_type = serializers.CharField(
        source='exercise.type.name',
        read_only=True
    )

    class Meta:
        model = ExerciseSession
        fields = [
            'id',
            'exercise_title',
            'exercise_type',
            'difficulty',
            'score',
            'success',
            'started_at',
            'finished_at',
            'duration_seconds',
            'attempts_count',
        ]
        read_only_fields = fields


class AnswerDetailSerializer(serializers.ModelSerializer):
    """
    Детальный просмотр ответа пользователя.
    """
    question_text = serializers.SerializerMethodField()
    user_answer = serializers.SerializerMethodField()
    correct_answer = serializers.SerializerMethodField()

    class Meta:
        model = UserAnswer
        fields = [
            'id',
            'question_text',
            'user_answer',
            'correct_answer',
            'is_correct',
            'response_time',
        ]

    def get_question_text(self, obj):
        """Извлекаем текст вопроса из JSON."""
        return obj.answer_data.get('question_text', '')

    def get_user_answer(self, obj):
        """Извлекаем ответ пользователя из JSON."""
        return obj.answer_data.get('user_answer')

    def get_correct_answer(self, obj):
        """Извлекаем правильный ответ из JSON."""
        return obj.answer_data.get('correct_answer')


class HistoryDetailSerializer(serializers.ModelSerializer):
    """
    Детальный просмотр прохождения упражнения (с ответами).
    GET /api/progress/history/<id>/
    """
    exercise_title = serializers.CharField(
        source='exercise.title',
        read_only=True
    )
    exercise_type = serializers.CharField(
        source='exercise.type.name',
        read_only=True
    )
    answers = AnswerDetailSerializer(many=True, read_only=True)

    class Meta:
        model = ExerciseSession
        fields = [
            'id',
            'exercise_title',
            'exercise_type',
            'difficulty',
            'started_at',
            'finished_at',
            'duration_seconds',
            'score',
            'success',
            'attempts_count',
            'answers',
        ]
        read_only_fields = fields


class StartExerciseSerializer(serializers.Serializer):
    """
    Сериализатор для старта задания.
    """
    exercise_id = serializers.IntegerField()

    def validate_exercise_id(self, value):
        """Проверяем, что задание существует и активно."""
        from backend.exercises.models import Exercise

        if not Exercise.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError(
                'Задание не найдено или недоступно'
            )
        return value


class SubmitAnswerSerializer(serializers.Serializer):
    """
    Сериализатор для отправки ответа.
    """
    question_id = serializers.IntegerField(required=True, min_value=0)
    answer = serializers.JSONField(required=True)
    response_time = serializers.FloatField(required=True, min_value=0)


class FinishExerciseSerializer(serializers.Serializer):
    """
    Сериализатор для завершения сессии.
    """
    confirm = serializers.BooleanField(default=True)
