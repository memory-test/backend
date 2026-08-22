from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from exercises.constants import (
    ANSWER_LIMIT,
    ANSWERS_GROUP_LIMIT,
    EX_DESC_LENGTH,
    EX_TITLE_LENGTH,
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
        return max(len(value) if value else 0 for value, _ in cls.choices)


class Exercise(models.Model):
    """Модель заданий."""

    title = models.CharField(
        'Название', max_length=EX_TITLE_LENGTH, unique=True
    )
    description = models.TextField('Описание', max_length=EX_DESC_LENGTH)
    type = models.CharField(
        'Тип задания',
        choices=ExerciseType.choices,
        max_length=ExerciseType.get_max_length(),
    )
    difficulty = models.CharField(
        'Уровень сложности',
        max_length=Difficulty.get_max_length(),
        choices=Difficulty.choices,
        default=Difficulty.EASY,
    )
    question = models.TextField('Текст вопроса', max_length=QUESTION_LIMIT)
    image = models.ImageField('Изображение вопроса', blank=True)
    audio = models.FileField('Аудио-вопрос', blank=True)
    is_active = models.BooleanField('Доступно к решению')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

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


class TextImageMixin(models.Model):
    """Миксин с полями "текст" и "изображение" для моделей ответов."""

    text = models.TextField('Текст', max_length=ANSWER_LIMIT, blank=True)
    image = models.ImageField('Изображение', blank=True)

    class Meta:
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


class InputAnswer(Answer):
    """Ответы с ручным вводом."""

    exercise = models.OneToOneField(
        Exercise, models.CASCADE, verbose_name='Задание'
    )
    expected_text = models.TextField(
        'Ожидаемый текст ответа', max_length=ANSWER_LIMIT
    )


class ChoiceAnswer(TextImageMixin, Answer):
    """Ответы с выбором варианта(ов)."""

    is_correct = models.BooleanField('Верный')

    def __str__(self):
        return super().__str__()

    class Meta(TextImageMixin.Meta, Answer.Meta):
        ordering = [
            'is_correct',
        ]


class OrderingAnswer(TextImageMixin, Answer):
    """Ответы для заданий с распределением элементов."""

    position = models.SmallIntegerField('Порядок')

    class Meta(TextImageMixin.Meta, Answer.Meta):
        ordering = [
            'position',
        ]


class GroupingAnswer(TextImageMixin, Answer):
    """Ответы для заданий на группировку."""

    group = models.CharField('Группа', max_length=ANSWERS_GROUP_LIMIT)

    class Meta(TextImageMixin.Meta, Answer.Meta):
        ordering = [
            'group',
        ]


class MatchingAnswer(Answer):
    """Ответы для заданий на сопоставление."""

    first_text = models.TextField(
        'Первый текст пары', max_length=ANSWER_LIMIT, blank=True
    )
    first_image = models.ImageField('Первое изображение пары', blank=True)
    second_text = models.TextField(
        'Второй текст пары', max_length=ANSWER_LIMIT, blank=True
    )
    second_image = models.ImageField('Второе изображение пары', blank=True)

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


class DrawingAnswer(TextImageMixin, Answer):
    """Ответы для графических заданий."""

    completion_only = models.BooleanField('Только фиксация выполнения')
    trajectory = models.JSONField(
        'Траектория (координаты)',
        blank=True,
        null=True,
    )
    tolerance = models.SmallIntegerField(
        'Допустимое отклонение',
        blank=True,
        null=True,
    )
    additional_image = models.ImageField(
        'Дополнительное изображение', blank=True
    )

    class Meta(TextImageMixin.Meta, Answer.Meta):
        constraints = [
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
        ]
