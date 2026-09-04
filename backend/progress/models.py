from django.conf import settings
from django.db import models

from exercises.models import Exercise
from users.models import Difficulty

MAX_DIFFICULTY_LEN = 10


class ExerciseSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='exercise_sessions',
        verbose_name='Пользователь',
    )
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name='Задание',
    )
    difficulty = models.CharField(
        max_length=MAX_DIFFICULTY_LEN,
        choices=Difficulty.choices,
        verbose_name='уровень сложности',
    )
    started_at = models.DateTimeField(verbose_name='Время начала')
    finished_at = models.DateTimeField(verbose_name='Время окончания')
    duration_seconds = models.IntegerField(verbose_name='Длительность (сек)')
    success = models.BooleanField(verbose_name='Успешно выполнено')
    score = models.FloatField(verbose_name='Оценка')

    class Meta:
        verbose_name = 'Сессия упражнения'
        verbose_name_plural = 'Сессии упражнений'
        ordering = ['-started_at']


class UserAttempt(models.Model):
    session = models.OneToOneField(
        'ExerciseSession',
        on_delete=models.CASCADE,
        related_name='attempt',
        verbose_name='Сессия упражнения',
    )
    answer_data = models.JSONField(verbose_name='Данные ответа (JSON)')

    class Meta:
        verbose_name = 'Ответ пользователя'
        verbose_name_plural = 'Ответы пользователей'
        ordering = ['id']
