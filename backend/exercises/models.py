from django.db import models

from common.choices import Difficulty
from exercises.constants import (
    EX_DESC_LENGTH,
    EX_TITLE_LENGTH,
    STR_LIMIT,
    TYPE_NAME_LENGTH,
    TYPY_DESC_LENGTH,
)


class ExerciseType(models.Model):
    """Модель типов заданий."""

    name = models.CharField(
        'Наименование', max_length=TYPE_NAME_LENGTH, unique=True
    )
    description = models.TextField('Описание', max_length=TYPY_DESC_LENGTH)

    class Meta:
        verbose_name = 'тип задания'
        verbose_name_plural = 'Типы заданий'
        ordering = [
            'name',
        ]

    def __str__(self):
        return self.name[:STR_LIMIT]


class Exercise(models.Model):
    """Модель заданий."""

    title = models.CharField(
        'Название', max_length=EX_TITLE_LENGTH, unique=True
    )
    description = models.TextField('Описание', max_length=EX_DESC_LENGTH)
    type = models.ForeignKey(
        ExerciseType, on_delete=models.CASCADE, verbose_name='Тип задания'
    )
    difficulty = models.CharField(
        'Уровень сложности',
        max_length=Difficulty.max_length,
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
        return self.title[:STR_LIMIT]
