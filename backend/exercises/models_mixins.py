from django.db import models
from django.db.models import Q

from exercises.constants import ANSWER_LIMIT
from exercises.models import Exercise


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
