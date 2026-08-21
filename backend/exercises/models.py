from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from exercises.constants import (
    ANSWER_LIMIT,
    ANSWERS_GROUP_LIMIT,
    DESC_LENGTH,
    EX_TITLE_LENGTH,
    QUESTION_LIMIT,
    TYPE_NAME_LENGTH,
)
from users.models import Difficulty


class ExerciseBase(models.Model):
    """
    Абстрактная модель для моделей приложения "Задания".

    Содержит общее поле "Описание" для типов и самих заданий.
    """

    description = models.TextField('Описание', max_length=DESC_LENGTH)

    class Meta:
        abstract = True


class ExerciseType(ExerciseBase):
    """Модель типов заданий."""

    name = models.CharField(
        'Наименование', max_length=TYPE_NAME_LENGTH, unique=True
    )
    slug = models.SlugField('Идентификатор', unique=True)

    class Meta:
        verbose_name = 'тип задания'
        verbose_name_plural = 'Типы заданий'
        ordering = [
            'name',
        ]

    def __str__(self):
        return self.name


class Exercise(ExerciseBase):
    """Модель заданий."""

    title = models.CharField(
        'Название', max_length=EX_TITLE_LENGTH, unique=True
    )
    type = models.ForeignKey(
        ExerciseType, on_delete=models.CASCADE, verbose_name='Тип задания'
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
        absract = True
        constraints = [
            models.CheckConstraint(
                condition=~Q(text='') | ~Q(image=''),
                name='text_or_image_required',
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
                name='texts_or_images_required',
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
