from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from exercises.constants import (
    ANSWER_LIMIT,
    ANSWERS_GROUP_LIMIT,
    EXERCISE_DESCRIPTION_LENGTH,
    EXERCISE_TITLE_LENGTH,
    QUESTION_LIMIT,
)
from users.models import Difficulty


class ExerciseType(models.TextChoices):
    """Типы заданий."""

    __empty__ = 'Выберите тип задания'

    CHOICE = 'choice', 'Выбор ответа(ов)'
    INPUT = 'input', 'Ручной ввод ответа'
    ORDERING = 'ordering', 'Сортировка'
    GROUPING = 'grouping', 'Группировка'
    MATCHING = 'matching', 'Сопоставление'
    DRAWING = 'drawing', 'Графическое задание'
    OFFLINE = 'offline', 'Офлайн задание'

    @classmethod
    def get_max_length(cls) -> int:
        length_values = (
            len(value) if value else 0 for value, _ in cls.choices
        )
        return max(length_values)


class Exercise(models.Model):
    """Модель заданий."""

    title = models.CharField(
        'Название',
        max_length=EXERCISE_TITLE_LENGTH,
        unique=True,
        help_text=(
            'Название упражнения, отображаемое в списке и карточке задания.'
        ),
    )
    description = models.TextField(
        'Описание',
        max_length=EXERCISE_DESCRIPTION_LENGTH,
        help_text='Краткое описание задания для пользователя (цели, формат).',
    )
    type = models.CharField(
        'Тип задания',
        choices=ExerciseType.choices,
        max_length=ExerciseType.get_max_length(),
        help_text=(
            'Тип упражнения: choice, input, ordering, grouping, matching, '
            'drawing, offline.'
        ),
    )
    difficulty = models.CharField(
        'Уровень сложности',
        max_length=Difficulty.get_max_length(),
        choices=Difficulty.choices,
        default=Difficulty.EASY,
        help_text=(
            'Сложность задания: easy, medium, hard (влияет на '
            'начисление баллов).'
        ),
    )
    question = models.TextField(
        'Текст вопроса',
        max_length=QUESTION_LIMIT,
        help_text=(
            'Основной текст вопроса/задания, который видит пользователь.'
        ),
    )
    image = models.ImageField(
        'Изображение вопроса',
        blank=True,
        help_text='Изображение к вопросу.',
    )
    audio = models.FileField(
        'Аудио-вопрос',
        blank=True,
        help_text='Аудиофайл к заданию (например, для аудирования).',
    )
    is_active = models.BooleanField(
        'Доступно к решению',
        help_text='Флаг доступности упражнения для прохождения.',
    )
    created_at = models.DateTimeField(
        'Дата создания',
        auto_now_add=True,
        help_text='Дата и время создания упражнения (автоматически).',
    )

    ANSWER_RELATIONS = {
        value: f'{value}answers' for value, _ in ExerciseType.choices
    }

    def has_answers(self):
        """Проверка на существование ответа(ов) к заданию."""
        if self.type == 'offline':
            return True
        if not self.pk:
            return False

        relation_name = self.ANSWER_RELATIONS.get(self.type)
        if relation_name is None:
            return False
        if self.type == 'input':
            return hasattr(self, relation_name)
        return getattr(self, relation_name).exists()

    def clean(self):
        super().clean()

        if self.is_active and not self.has_answers():
            raise ValidationError(
                {
                    'is_active': ('Нельзя активировать задание без ответа.'),
                }
            )

    class Meta:
        verbose_name = 'задание'
        verbose_name_plural = 'Задания'
        ordering = [
            'title',
        ]

    def __str__(self):
        return self.title


class Answer(models.Model):
    """Абстрактная модель для ответов на задания."""

    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        verbose_name='Задание',
        related_name='%(class)ss',
    )

    class Meta:
        abstract = True
        verbose_name = 'ответ'
        verbose_name_plural = 'Ответы'

    def __str__(self):
        return f'Ответ на задание №{self.exercise.id}'


class AnswerTextImageFields(Answer):
    """Абстрактная модель ответов с полями "текст" и "изображение"."""

    text = models.TextField(
        'Текст',
        max_length=ANSWER_LIMIT,
        blank=True,
        help_text='Текстовое содержание ответа.',
    )
    image = models.ImageField(
        'Изображение',
        blank=True,
        help_text='Изображение ответа.',
    )

    class Meta(Answer.Meta):
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=~Q(text='') | ~Q(image=''),
                name='%(app_label)s_%(class)s_text_or_image_required',
                violation_error_message=(
                    'Необходимо заполнить текст ответа или загрузить '
                    'изображение.'
                ),
            )
        ]


# Модели ответов необходимо именовать в соответсвии с их типом по схеме:
# class TypeAnswer(Answer)


class InputAnswer(Answer):
    """Ответы с ручным вводом."""

    exercise = models.OneToOneField(
        Exercise,
        models.CASCADE,
        verbose_name='Задание',
        related_name='inputanswers',
    )
    expected_text = models.TextField(
        'Ожидаемый текст ответа', max_length=ANSWER_LIMIT
    )


class ChoiceAnswer(AnswerTextImageFields):
    """Ответы с выбором варианта(ов)."""

    is_correct = models.BooleanField(
        'Верный',
        help_text=(
            'Признак правильности варианта (используется при проверке и '
            'показе эталона).'
        ),
    )

    class Meta(AnswerTextImageFields.Meta):
        ordering = [
            'is_correct',
        ]


class OrderingAnswer(AnswerTextImageFields):
    """Ответы для заданий с распределением элементов."""

    position = models.SmallIntegerField(
        'Порядок',
        help_text=(
            'Ожидаемый порядковый номер элемента в правильной '
            'последовательности.'
        ),
    )

    class Meta(AnswerTextImageFields.Meta):
        ordering = [
            'position',
        ]


class GroupingAnswer(AnswerTextImageFields):
    """Ответы для заданий на группировку."""

    group = models.CharField(
        'Группа',
        max_length=ANSWERS_GROUP_LIMIT,
        help_text=(
            'Имя группы/категории, к которой относится элемент '
            "(например, 'фрукты')."
        ),
    )

    class Meta(AnswerTextImageFields.Meta):
        ordering = [
            'group',
        ]


class MatchingAnswer(Answer):
    """Ответы для заданий на сопоставление."""

    first_text = models.TextField(
        'Первый текст пары',
        max_length=ANSWER_LIMIT,
        blank=True,
        help_text='Текст первого элемента пары для сопоставления.',
    )
    first_image = models.ImageField(
        'Первое изображение пары',
        blank=True,
        help_text='Изображение первого элемента пары.',
    )
    second_text = models.TextField(
        'Второй текст пары',
        max_length=ANSWER_LIMIT,
        blank=True,
        help_text='Текст второго элемента пары для сопоставления.',
    )
    second_image = models.ImageField(
        'Второе изображение пары',
        blank=True,
        help_text='Изображение второго элемента пары.',
    )

    class Meta(Answer.Meta):
        constraints = [
            models.CheckConstraint(
                condition=(
                    (~Q(first_text='') | ~Q(first_image=''))
                    & (~Q(second_text='') | ~Q(second_image=''))
                ),
                name='%(app_label)s_%(class)s_texts_or_images_required',
                violation_error_message=(
                    'Необходимо заполнить текст ответа или загрузить '
                    'изображение в каждом элементе пары.'
                ),
            )
        ]


class DrawingAnswer(AnswerTextImageFields):
    """Ответы для графических заданий."""

    completion_only = models.BooleanField(
        'Только фиксация выполнения',
        help_text=(
            'Если True, достаточно просто зафиксировать факт выполнения.'
        ),
    )
    trajectory = models.JSONField(
        'Траектория (координаты)',
        blank=True,
        null=True,
        help_text='Координаты траектории рисунка пользователя.',
    )
    tolerance = models.SmallIntegerField(
        'Допустимое отклонение',
        blank=True,
        null=True,
        help_text='Допустимое отклонение от эталонной траектории.',
    )
    additional_image = models.ImageField(
        'Дополнительное изображение',
        blank=True,
        help_text=(
            'Эталонное или вспомогательное изображение для проверки '
            'графического ответа.'
        ),
    )

    class Meta(AnswerTextImageFields.Meta):
        constraints = AnswerTextImageFields.Meta.constraints
        constraints.append(
            models.CheckConstraint(
                condition=(
                    Q(completion_only=True)
                    | (
                        Q(trajectory__isnull=False)
                        & Q(tolerance__isnull=False)
                    )
                ),
                name='params_required_unless_completion_only',
                violation_error_message='Необходимо заполнить поля ответа.',
            ),
        )
