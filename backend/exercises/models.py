from django.db import models

from exercises.constants import (
    DESC_LENGTH,
    EX_TITLE_LENGTH,
    TYPE_NAME_LENGTH,
)
from users.models import Difficulty


class ExerciseBase(models.Model):
    """
    Абстрактная модель для моделей приложения "Задания".

    Содержит общее поле "Описание".
    """

    description = models.TextField('Описание', max_length=DESC_LENGTH)

    class Meta:
        abstract = True


class ExerciseType(ExerciseBase):
    """Модель типов заданий."""

    name = models.CharField(
        'Наименование', max_length=TYPE_NAME_LENGTH, unique=True
    )

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
    config = models.JSONField('Настройки задания')
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
