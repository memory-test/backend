from rest_framework import serializers

from authentication import services
from authentication.constants import CODE_LENGTH
from exercises.models import Exercise, ChoiceAnswer
from progress.models import ExerciseSession, UserAnswer
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

class ChoiceAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChoiceAnswer
        fields = ['id', 'text', 'image']

class ChoiceExerciseSerializer(serializers.ModelSerializer):
    options = ChoiceAnswerSerializer(many=True, read_only=True, source='choiceanswers')

    class Meta:
        model = Exercise
        fields = ['id', 'title', 'description', 'question', 'image', 'audio', 'options']


class ChoiceCheckSerializer(serializers.Serializer):
    answers_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )

    def validate(self, attrs):
        exercise = self.context.get('exercise')
        user_answers_ids = list(set(attrs.get('answers_ids')))
        allowed_ids = [answer.id for answer in exercise.choiceanswers.all()]
        for answer_id in user_answers_ids:
            if answer_id not in allowed_ids:
                raise serializers.ValidationError(
                    {'answers_ids': f'Вариант ответа с ID {answer_id} не принадлежит данному заданию.'}
                )
        attrs['answers_ids'] = user_answers_ids
        return attrs



class ResultExerciseSerializer(serializers.Serializer):
    score = serializers.FloatField(required=True)
    success = serializers.BooleanField(required=True)

# TODO: будет изменена модель,
#  следовательно надо будет изменить сериализатор.
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
    """Список краткой истории прохождения упражнений."""

    exercise_title = serializers.CharField(
        source='exercise.title', read_only=True
    )
    exercise_type = serializers.CharField(
        source='exercise.type.name', read_only=True
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
    """Детальный просмотр ответа пользователя."""

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
    """Детальный просмотр прохождения упражнения (с ответами)."""

    exercise_title = serializers.CharField(
        source='exercise.title', read_only=True
    )
    exercise_type = serializers.CharField(
        source='exercise.type.name', read_only=True
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
