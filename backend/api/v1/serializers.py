from rest_framework import serializers

from authentication import services
from authentication.constants import CODE_LENGTH
from exercises.models import (
    ChoiceAnswer,
    DrawingAnswer,
    Exercise,
    ExerciseType,
    GroupingAnswer,
    MatchingAnswer,
    OrderingAnswer,
)
from users.constants import EMAIL_LENGTH
from users.models import Difficulty


class AnswerBaseSerializer(serializers.ModelSerializer):
    """Сериализатор ответов с полями "текст" и "изображение".

    Только для наследования, не применяется напрямую.
    """

    class Meta:
        fields = (
            'text',
            'image',
        )


class ChoiceAnswerSerializer(AnswerBaseSerializer):
    """Сериализатор ответов на выбор варианта(ов)."""

    class Meta(AnswerBaseSerializer.Meta):
        model = ChoiceAnswer


class OrderingAnswerSerializer(AnswerBaseSerializer):
    """Сериализатор ответов на сортировку."""

    class Meta(AnswerBaseSerializer.Meta):
        model = OrderingAnswer


class GroupingAnswerSerializer(AnswerBaseSerializer):
    """Сериализатор ответов на группировку."""

    class Meta(AnswerBaseSerializer.Meta):
        model = GroupingAnswer


class MatchingAnswerSerializer(serializers.ModelSerializer):
    """Сериализатор ответов на сопоставление."""

    class Meta:
        model = MatchingAnswer
        fields = (
            'first_text',
            'first_image',
            'second_text',
            'second_image',
        )


class DrawingAnswerSerializer(AnswerBaseSerializer):
    """Сериализатор графических ответов."""

    class Meta(AnswerBaseSerializer.Meta):
        model = DrawingAnswer
        fields = AnswerBaseSerializer.Meta.fields + (
            'completion_only',
            'additional_image',
        )


class ExerciseSerializer(serializers.ModelSerializer):
    """Сериализатор объектов класса Exercise."""

    type = serializers.ChoiceField(ExerciseType.choices)
    difficulty = serializers.ChoiceField(Difficulty.choices)
    answers_info = serializers.SerializerMethodField(read_only=True)

    ANSWER_SERIALIZERS = {
        ExerciseType.CHOICE: ChoiceAnswerSerializer,
        ExerciseType.ORDERING: OrderingAnswerSerializer,
        ExerciseType.GROUPING: GroupingAnswerSerializer,
        ExerciseType.MATCHING: MatchingAnswerSerializer,
        ExerciseType.DRAWING: DrawingAnswerSerializer,
    }

    def get_answers_info(self, obj: Exercise):
        serializer_class = self.ANSWER_SERIALIZERS.get(obj.type)
        if serializer_class is None:
            return []
        relation_name = obj.ANSWER_RELATIONS.get(obj.type)
        answers = getattr(obj, relation_name).all()

        return serializer_class(
            answers,
            many=True,
            context=self.context,
        ).data

    class Meta:
        model = Exercise
        fields = (
            'id',
            'title',
            'description',
            'type',
            'difficulty',
            'question',
            'image',
            'audio',
            'is_active',
            'created_at',
            'answers_info',
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
