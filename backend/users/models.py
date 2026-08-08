from django.contrib.auth.models import AbstractUser
from django.db import models

from users import constants


class Difficulty(models.TextChoices):
    """Уровни сложности."""

    EASY = 'easy', 'Лёгкий'
    MEDIUM = 'medium', 'Средний'
    HARD = 'hard', 'Сложный'

    @classmethod
    def get_max_length(cls) -> int:
        return max(len(value) for value, _ in cls.choices)


class User(AbstractUser):
    """Кастомная модель пользователя."""

    class Role(models.TextChoices):
        """Роли пользователя."""

        USER = ('user', 'Пользователь')
        ADMIN = ('admin', 'Администратор')

    name = models.CharField(
        max_length=constants.NAME_LENGTH, verbose_name='Имя'
    )
    birth_date = models.DateField(
        null=True, blank=True, verbose_name='Дата рождения'
    )
    current_difficulty = models.CharField(
        max_length=constants.CURRENT_DIFFICULTY_LENGTH,
        choices=Difficulty.choices,
        default=Difficulty.EASY,
        verbose_name='Уровень сложности',
    )
    role = models.CharField(
        max_length=constants.ROLE_LENGTH,
        choices=Role.choices,
        default=Role.USER,
        verbose_name='Роль',
    )

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        """Возвращает строковое представление."""
        return self.name
