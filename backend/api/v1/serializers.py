import random
from dataclasses import dataclass

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiTypes,
    extend_schema_field,
    extend_schema_serializer,
)
from rest_framework import serializers

from authentication.constants import CODE_LENGTH
from authentication.models import EmailCode
from exercises.models import (
    ChoiceAnswer,
    DrawingAnswer,
    Exercise,
    ExerciseType,
    GroupingAnswer,
    InputAnswer,
    OrderingAnswer,
)
from progress.models import ExerciseSession, UserAttempt
from users.constants import EMAIL_LENGTH


class AnswerBaseSerializer(serializers.ModelSerializer):
    """Базовый сериализатор ответов с полями «текст» и «изображение».

    Только для наследования, не применяется напрямую.
    """

    class Meta:
        fields = (
            'text',
            'image',
        )


class ChoiceAnswerSerializer(AnswerBaseSerializer):
    """Сериализатор ответов на выбор варианта(ов)."""

    is_correct = serializers.SerializerMethodField(
        help_text=(
            'Признак правильности варианта (используется при проверке и '
            'показе эталона).'
        ),
    )

    class Meta(AnswerBaseSerializer.Meta):
        model = ChoiceAnswer
        fields = AnswerBaseSerializer.Meta.fields + ('id', 'is_correct')

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_correct(self, obj):
        return obj.is_correct

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not self.context.get('show_correct', False):
            data.pop('is_correct', None)
        return data


class OrderingAnswerSerializer(AnswerBaseSerializer):
    """Сериализатор ответов на сортировку."""

    class Meta(AnswerBaseSerializer.Meta):
        model = OrderingAnswer
        fields = AnswerBaseSerializer.Meta.fields + ('id', 'position')


class GroupingAnswerSerializer(AnswerBaseSerializer):
    """Сериализатор ответов на группировку."""

    class Meta(AnswerBaseSerializer.Meta):
        model = GroupingAnswer
        fields = AnswerBaseSerializer.Meta.fields + ('id', 'group')


class DrawingAnswerSerializer(AnswerBaseSerializer):
    """Сериализатор графических ответов."""

    class Meta(AnswerBaseSerializer.Meta):
        model = DrawingAnswer
        fields = AnswerBaseSerializer.Meta.fields + (
            'id',
            'completion_only',
            'additional_image',
        )


class BaseCheckSerializer(serializers.Serializer):
    """Базовый сериализатор для проверки ответов с метаданными времени."""

    started_at = serializers.DateTimeField(
        required=True,
        help_text='Время начала выполнения задания (ISO 8601)',
    )
    finished_at = serializers.DateTimeField(
        required=True,
        help_text='Время окончания выполнения задания (ISO 8601)',
    )
    duration_seconds = serializers.IntegerField(
        required=True,
        help_text='Длительность выполнения в секундах',
    )

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


class ChoiceCheckSerializer(BaseCheckSerializer):
    """Сериалайзер для проверки ответов типа choice."""

    answers_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
        help_text='Список ID выбранных вариантов ответа (из answers_info)',
    )

    def validate(self, attrs):
        exercise = self.context.get('exercise')
        user_answers_ids = list(set(attrs.get('answers_ids')))
        allowed_ids = [answer.id for answer in exercise.choiceanswers.all()]
        for answer_id in user_answers_ids:
            if answer_id not in allowed_ids:
                raise serializers.ValidationError(
                    {
                        'answers_ids': (
                            f'Вариант ответа с ID {answer_id} '
                            'не принадлежит данному заданию.'
                        )
                    }
                )
        attrs['answers_ids'] = user_answers_ids
        return attrs


@dataclass
class MatchingCard:
    """Единообразное представление одной карточки — что для левой,
    что для правой стороны, хотя в MatchingAnswer поля называются
    по-разному (first_*/second_*)."""

    id: int
    text: str | None
    image: object  # ImageFieldFile или None


class MatchingCardSerializer(serializers.Serializer):
    """Одна карточка для сопоставления: id, текст и/или картинка."""

    id = serializers.IntegerField()
    text = serializers.CharField(allow_null=True)
    image = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_image(self, obj: MatchingCard):
        return obj.image.url if obj.image else None


class MatchingAnswerSerializer(serializers.Serializer):
    """Левые и правые карточки для matching, раздельно и без связи
    между ними — иначе пары были бы видны заранее."""

    left = serializers.SerializerMethodField()
    right = serializers.SerializerMethodField()

    def get_left(self, pairs):
        cards = [
            MatchingCard(p.id, p.first_text or None, p.first_image)
            for p in pairs
        ]
        return MatchingCardSerializer(cards, many=True).data

    def get_right(self, pairs):
        cards = [
            MatchingCard(p.id, p.second_text or None, p.second_image)
            for p in pairs
        ]
        random.shuffle(cards)
        return MatchingCardSerializer(cards, many=True).data


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Пример запроса (matching)',
            value={
                'started_at': '2026-09-07T14:30:00Z',
                'finished_at': '2026-09-07T14:30:30Z',
                'duration_seconds': 30,
                'pairs': [
                    {'first_id': 1, 'second_id': 1},
                    {'first_id': 2, 'second_id': 2},
                ],
            },
        ),
    ],
)
class MatchingCheckSerializer(BaseCheckSerializer):
    """Сериалайзер для проверки ответов типа matching."""

    pairs = serializers.ListField(
        child=serializers.DictField(child=serializers.IntegerField()),
        allow_empty=False,
        help_text=(
            'Список пар вида {"first_id": <id>, "second_id": <id>} — '
            'id карточек из левого и правого списков (answers_info).'
        ),
    )

    def validate_pairs(self, value):
        for pair in value:
            if set(pair.keys()) != {'first_id', 'second_id'}:
                raise serializers.ValidationError(
                    'Каждая пара должна содержать поля first_id и second_id.'
                )
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        exercise = self.context.get('exercise')
        allowed_ids = {a.id for a in exercise.matchinganswers.all()}
        for pair in attrs['pairs']:
            if (
                pair['first_id'] not in allowed_ids
                or pair['second_id'] not in allowed_ids
            ):
                raise serializers.ValidationError(
                    {'pairs': 'Элемент пары не принадлежит данному заданию.'}
                )
        return attrs


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Результат прохождения',
            value={'score': 0.67, 'success': False},
        ),
    ],
)
class ResultExerciseSerializer(serializers.Serializer):
    """Результат проверки ответа пользователя."""

    score = serializers.FloatField(
        required=True,
        help_text='Оценка за упражнение (0.0–1.0)',
    )
    success = serializers.BooleanField(
        required=True,
        help_text='Признак успешного прохождения',
    )


class InputCheckSerializer(BaseCheckSerializer):
    """Сериалайзер для проверки ответов типа input."""

    answers = serializers.ListField(
        child=serializers.CharField(allow_blank=False, trim_whitespace=False),
        allow_empty=False,
        help_text=(
            'Ответ(ы) пользователя. Формат зависит от check_method эталона.'
        ),
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        exercise = self.context.get('exercise')
        answer = exercise.inputanswers.first() if exercise else None
        if answer is None:
            raise serializers.ValidationError(
                {'detail': 'Для задания не настроен эталонный ответ.'}
            )

        method = answer.check_method
        if (
            method
            in (
                InputAnswer.CheckMethod.SINGLE_ANSWER,
                InputAnswer.CheckMethod.FREE_ANSWER,
            )
            and len(attrs['answers']) != 1
        ):
            raise serializers.ValidationError(
                {'answers': 'Для этого задания нужен ровно один ответ.'}
            )
        return attrs


class ExerciseShortSerializer(serializers.ModelSerializer):
    """Сериализатор краткого представления объектов класса Exercise.

    Для использования при отображении списка заданий.
    """

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


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Детальное задание с ответами',
            value={
                'id': 42,
                'title': 'Запоминание слов',
                'description': (
                    'Запомните список слов, затем выберите те, что были в '
                    'списке'
                ),
                'type': 'choice',
                'difficulty': 'easy',
                'question': 'Какие из этих слов были в исходном списке?',
                'image': None,
                'audio': None,
                'is_active': True,
                'created_at': '2026-09-07T14:15:30Z',
                'answers_info': [
                    {'id': 101, 'text': 'Яблоко', 'image': None},
                    {'id': 102, 'text': 'Зонт', 'image': None},
                    {'id': 103, 'text': 'Ключ', 'image': None},
                    {'id': 104, 'text': 'Молоток', 'image': None},
                ],
            },
        ),
    ],
)
class ExerciseFullSerializer(ExerciseShortSerializer):
    """Сериализатор полного представления объектов класса Exercise."""

    answers_info = serializers.SerializerMethodField(
        read_only=True,
        help_text=(
            'Для choice/ordering/grouping/drawing — список вариантов '
            'ответа. Для matching — {"left": [...], "right": [...]}, '
            'каждая карточка: {"id", "text", "image"} (карточки '
            'раздельно, правая колонка перемешана). Для input — всегда '
            'пустой список (эталон скрыт).'
        ),
    )

    ANSWER_SERIALIZERS = {
        ExerciseType.CHOICE: ChoiceAnswerSerializer,
        ExerciseType.ORDERING: OrderingAnswerSerializer,
        ExerciseType.GROUPING: GroupingAnswerSerializer,
        ExerciseType.MATCHING: MatchingAnswerSerializer,
        ExerciseType.DRAWING: DrawingAnswerSerializer,
    }

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_answers_info(self, obj: Exercise):
        serializer_class = self.ANSWER_SERIALIZERS.get(obj.type)
        if serializer_class is None:
            return []
        relation_name = obj.ANSWER_RELATIONS.get(obj.type)
        answers = getattr(obj, relation_name).all()

        many = obj.type != ExerciseType.MATCHING
        return serializer_class(
            answers,
            many=many,
            context=self.context,
        ).data

    class Meta(ExerciseShortSerializer.Meta):
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


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Элемент истории',
            value={
                'id': 1,
                'exercise_title': 'Запоминание слов',
                'exercise_type': 'choice',
                'difficulty': 'easy',
                'score': 1.0,
                'success': True,
                'started_at': '2026-09-07T14:30:00Z',
                'finished_at': '2026-09-07T14:32:15Z',
                'duration_seconds': 135,
            },
        ),
    ],
)
class HistoryListSerializer(serializers.ModelSerializer):
    """Список краткой истории прохождения упражнений."""

    exercise_title = serializers.CharField(
        source='exercise.title', read_only=True
    )
    exercise_type = serializers.CharField(
        source='exercise.type', read_only=True
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
        ]
        read_only_fields = fields


class UserAttemptSerializer(serializers.ModelSerializer):
    """Детальный просмотр попытки пользователя."""

    class Meta:
        model = UserAttempt
        fields = ['id', 'answer_data']
        read_only_fields = fields


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Детальная история с попыткой',
            value={
                'id': 1,
                'exercise_title': 'Запоминание слов',
                'exercise_type': 'choice',
                'difficulty': 'easy',
                'started_at': '2026-09-07T14:30:00Z',
                'finished_at': '2026-09-07T14:32:15Z',
                'duration_seconds': 135,
                'score': 1.0,
                'success': True,
                'attempt': {
                    'id': 1,
                    'answer_data': {
                        'answers_ids': [101, 103],
                        'note': 'Содержимое зависит от типа задания',
                    },
                },
            },
        ),
    ],
)
class HistoryDetailSerializer(serializers.ModelSerializer):
    """Детальный просмотр прохождения упражнения (с ответами)."""

    exercise_title = serializers.CharField(
        source='exercise.title', read_only=True
    )
    exercise_type = serializers.CharField(
        source='exercise.type', read_only=True
    )
    attempt = UserAttemptSerializer(read_only=True)

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
            'attempt',
        ]
        read_only_fields = fields


VERIFY_PURPOSES = (
    (EmailCode.Purpose.REGISTRATION, 'Регистрация'),
    (EmailCode.Purpose.LOGIN, 'Вход'),
)


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Запрос кода',
            value={'email': 'user@example.com'},
        ),
    ],
)
class LoginCodeRequestSerializer(serializers.Serializer):
    """Запрос кода для входа (регистрация и сброс — эндпоинты djoser)."""

    email = serializers.EmailField(
        max_length=EMAIL_LENGTH,
        help_text='Email для отправки кода подтверждения',
    )


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Подтверждение входа',
            value={
                'email': 'user@example.com',
                'code': '123456',
                'purpose': 'login',
            },
        ),
    ],
)
class CodeVerifySerializer(serializers.Serializer):
    """Подтверждение кода (регистрация / вход) — возвращает JWT."""

    email = serializers.EmailField(
        max_length=EMAIL_LENGTH,
        help_text='Email пользователя',
    )
    code = serializers.CharField(
        max_length=CODE_LENGTH,
        min_length=1,
        trim_whitespace=True,
        help_text='Код подтверждения из письма',
    )
    purpose = serializers.ChoiceField(
        choices=VERIFY_PURPOSES,
        help_text="Цель: 'registration' — регистрация, 'login' — вход",
    )
