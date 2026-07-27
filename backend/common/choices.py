from django.db import models


class Difficulty(models.TextChoices):
    """Уровни сложности."""

    EASY = 'easy', 'Лёгкий'
    MEDIUM = 'medium', 'Средний'
    HARD = 'hard', 'Сложный'

    max_length: int


Difficulty.max_length = max(len(value) for value, _ in Difficulty.choices)
