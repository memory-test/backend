from django.db import models


class Difficulty(models.TextChoices):
    """Уровни сложности."""

    EASY = 'easy', 'Лёгкий'
    MEDIUM = 'medium', 'Средний'
    HARD = 'hard', 'Сложный'

    @classmethod
    def get_max_length(cls) -> int:
        return max(len(value) for value, _ in cls.choices)
