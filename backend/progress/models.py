from django.db import models
from django.conf import settings


MAX_DIFFICULTY_LEN = 10


class Difficulty(models.TextChoices):
    """Варианты уровня сложностей для заданий."""

    EASY = 'easy', 'Лёгкий'
    MEDIUM = 'medium', 'Средний'
    HARD = 'hard', 'Сложный'

class ExerciseSession(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='exercise_sessions',
        verbose_name='Пользователь'
    )
    exercise = models.ForeignKey(
        'trainings.TemporaryExerciseStub',
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name='Задание'
    )
    difficulty = models.CharField(
        max_length=MAX_DIFFICULTY_LEN,
        choices=Difficulty.choices,
        verbose_name='уровень сложности'
    )
    started_at = models.DateTimeField(
        verbose_name='Время начала'
    )
    finished_at = models.DateTimeField(
        verbose_name='Время окончания'
    )
    duration_seconds = models.IntegerField(
        verbose_name='Длительность (сек)'
    )
    success = models.BooleanField(
        verbose_name='Успешно выполнено'
    )
    score = models.FloatField(
        verbose_name='Оценка'
    )
    attempts_count = models.IntegerField(
        verbose_name='Количество попыток'
    )

    class Meta:
        db_table = 'exercise_sessions'
        verbose_name = 'Сессия упражнения'
        verbose_name_plural = 'Сессии упражнений'
        ordering = ['id']

    def __str__(self):
        return f"Сессия {self.id} | Пользователь {self.user_id}"


class UserAnswer(models.Model):
    session = models.ForeignKey(
        'ExerciseSession',
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name='Сессия упражнения'
    )
    answer_data = models.JSONField(
        verbose_name='Данные ответа (JSON)'
    )
    is_correct = models.BooleanField(
        verbose_name='Ответ верный'
    )
    response_time = models.FloatField(
        verbose_name='Время ответа (сек)'
    )

    class Meta:
        db_table = 'exercise_answers'
        verbose_name = 'Ответ пользователя'
        verbose_name_plural = 'Ответы пользователей'
        ordering = ['id']

    def __str__(self):
        return f"Ответ {self.id} | Сессия {self.session_id} | Статус: {self.is_correct}"

