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

    CHOICE = 'choice', 'Выбор ответа(ов)'
    INPUT = 'input', 'Ручной ввод ответа'
    ORDERING = 'ordering', 'Сортировка'
    GROUPING = 'grouping', 'Группировка'
    MATCHING = 'matching', 'Сопоставление'
    DRAWING = 'drawing', 'Графический вопрос'

    @classmethod
    def get_max_length(cls) -> int:
        return max(len(value) for value, _ in cls.choices)


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
    is_offline = models.BooleanField('Оффлайн задание')
    is_active = models.BooleanField('Доступно к решению')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

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
        Exercise, on_delete=models.CASCADE, verbose_name='Задание'
    )

    class Meta:
        abstract = True
        verbose_name = 'ответ'
        verbose_name_plural = 'Ответы'


class TextImageMixin(models.Model):
    """Миксин с полями "текст" и "изображение" для моделей ответов."""

    text = models.TextField('Текст', max_length=ANSWER_LIMIT, blank=True)
    image = models.ImageField('Изображение', blank=True)

    def clean(self):
        super().clean()

        if not self.text.strip() and not self.image:
            raise ValidationError(
                'Необходимо заполнить текст ответа или загрузить изображение.'
            )

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=~Q(text='') | ~Q(image=''),
                name='%(app_label)s_%(class)s_text_or_image_required',
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

    def __str__(self):
        return self.expected_text


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

    def clean(self):
        super().clean()

        if (
            not self.first_text.strip()
            and not self.first_image
            or not self.second_text.strip()
            and not self.second_image
        ):
            raise ValidationError(
                (
                    'Необходимо заполнить текст ответа или загрузить'
                    'изображение в каждом элементе пары.'
                )
            )

    class Meta(Answer.Meta):
        constraints = [
            models.CheckConstraint(
                condition=(
                    (~Q(first_text='') | ~Q(first_image=''))
                    & (~Q(second_text='') | ~Q(second_image=''))
                ),
                name='%(app_label)s_%(class)s_texts_or_images_required',
            )
        ]


class DrawingAnswer(TextImageMixin, Answer):
    """Ответы для графических заданий."""

    trajectory = models.JSONField('Траектория (координаты)')
    tolerance = models.SmallIntegerField('Допустимое отклонение')
    completion_only = models.BooleanField('Только фиксация выполнения')
    additional_image = models.ImageField(
        'Дополнительное изображение', blank=True
    )

    class Meta(TextImageMixin.Meta, Answer.Meta):
        pass
