from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
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
        help_text='Пользователь, который проходил упражнение.',
    )
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name='Задание',
        help_text='Упражнение, которое проходило.',
    )
    difficulty = models.CharField(
        max_length=MAX_DIFFICULTY_LEN,
        choices=Difficulty.choices,
        verbose_name='Уровень сложности',
        help_text='Уровень сложности на момент прохождения.',
    )
    started_at = models.DateTimeField(
        verbose_name='Время начала',
        help_text='Время начала попытки.',
    )
    finished_at = models.DateTimeField(
        verbose_name='Время окончания',
        help_text='Время завершения попытки.',
    )
    duration_seconds = models.PositiveIntegerField(
        verbose_name='Длительность (сек)',
        help_text=(
            'Длительность попытки в секундах '
            '(разница между finished_at и started_at).'
        ),
    )
    success = models.BooleanField(
        verbose_name='Успешно выполнено',
        help_text='Признак успешного прохождения упражнения.',
    )
    score = models.FloatField(
        verbose_name='Оценка',
        help_text='Оценка за попытку.',
    )

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
        help_text='Сессия, к которой относится попытка пользователя.',
    )
    answer_data = models.JSONField(
        verbose_name='Данные ответа (JSON)',
        help_text=(
            'Полные данные попытки: снимок упражнения, ответ пользователя, '
            'результат проверки и метаданные (хранится в формате JSON).'
        ),
        encoder=DjangoJSONEncoder,
    )

    class Meta:
        verbose_name = 'Ответ пользователя'
        verbose_name_plural = 'Ответы пользователей'
        ordering = ['id']
