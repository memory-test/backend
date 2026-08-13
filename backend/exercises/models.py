from django.db import models
from django.core.exceptions import ValidationError

from exercises.constants import (
    DESC_LENGTH,
    EX_TITLE_LENGTH,
    STR_LIMIT,
    TYPE_NAME_LENGTH,
)
from users.models import Difficulty


class ExerciseType(models.TextChoices):
    # здесь каждый при реализации, добавит свои типы заданий
    CHOICE = 'CHOICE', 'Тест (один или несколько вариантов)'
    MATCHING = 'MATCHING', 'Сопоставление пар'

class ExerciseBase(models.Model):
    # поле для указания типа задания,обязательное для дочерних моделей.
    EXERCISE_TYPE = None
    description = models.TextField('Описание', max_length=DESC_LENGTH)
    title = models.CharField(
        'Название', max_length=EX_TITLE_LENGTH, unique=True
    )
    # решил убрать дополнительную модель, так когда мы будем проверять корректность отввета,
    # сможем быстро получить его тип, без лишних запросов к таблице типов
    type = models.CharField(
        'Тип задания',
        max_length=TYPE_NAME_LENGTH,
        choices=ExerciseType.choices,
        editable=False
    )
    difficulty = models.CharField(
        'Уровень сложности',
        max_length=Difficulty.get_max_length(),
        choices=Difficulty.choices,
        default=Difficulty.EASY,
    )
    is_active = models.BooleanField('Доступно к решению')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Задание'
        verbose_name_plural = 'Все задания'

    def save(self, *args, **kwargs):
        if type(self) is ExerciseBase:
            raise ValidationError('Нельзя создавать объекты базового класса ExerciseBase.')

        # Проверка, чтобы не забыть указать тип в дочернем классе
        if self.EXERCISE_TYPE is None:
            raise NotImplementedError
        self.type = self.EXERCISE_TYPE
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Задание {self.title}, тип {self.EXERCISE_TYPE}'



class ChoiceExercise(ExerciseBase):
    """Модель описывает тип заданий с единственным или множественным выбором."""
    is_multiple = models.BooleanField(
        'Множественный выбор',
        default=False,
        help_text='Если отмечено, студент должен будет выбрать несколько вариантов ответа.'
    )

    class Meta:
        verbose_name = 'Тестовое задание'
        verbose_name_plural = 'Тестовые задания'

    def save(self, *args, **kwargs):
        self.type = ExerciseType.CHOICE
        super().save(*args, **kwargs)


class ChoiceOption(models.Model):
        """
        Модель описывает вариант ответа для заданий с единственным
        или множественным выбором. Один вариант относится
        только к одному заданию, так админ сможет гибко настраивать
        кол-во вариантов для каждого задания.
        """
        exercise = models.ForeignKey(
            ChoiceExercise,
            on_delete=models.CASCADE,
            related_name='options',  # Позволит делать запрос: exercise.options.all()
            verbose_name='Задание'
        )
        text = models.CharField(
            'Текст варианта ответа',
            max_length=EX_TITLE_LENGTH
        )
        # этим полем админ будет указывать
        # является ли этот вариант ответа правильным.
        is_correct = models.BooleanField(
            'Это правильный ответ',
            default=False
        )

    class Meta:
        verbose_name = 'Вариант ответа'
        verbose_name_plural = 'Варианты ответов'
        ordering = ['id']


    def __str__(self):
        return f'Вариант ответа для задания {self.exercise}.'

