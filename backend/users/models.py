from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

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

    username = None
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Role(models.TextChoices):
        """Роли пользователя."""

        USER = ('user', 'Пользователь')
        ADMIN = ('admin', 'Администратор')

    name = models.CharField(
        max_length=constants.NAME_LEN,
        verbose_name='Имя',
        help_text='Имя пользователя',
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата рождения',
        help_text='Дата рождения',
    )
    current_difficulty = models.CharField(
        max_length=constants.CURRENT_DIFFICULTY_LEN,
        choices=Difficulty.choices,
        default=Difficulty.EASY,
        verbose_name='Уровень сложности',
        help_text='Текущий уровень сложности',
    )
    role = models.CharField(
        max_length=constants.ROLE_LEN,
        choices=Role.choices,
        default=Role.USER,
        verbose_name='Роль',
        help_text='Роль пользователя',
    )
    email = models.EmailField(
        max_length=constants.EMAIL_LEN,
        unique=True,
        verbose_name='Электронная почта',
        help_text='Электронная почта пользователя',
    )
    password = models.CharField(
        max_length=constants.PASSWORD_LEN,
        verbose_name='Пароль',
        help_text='Пароль для доступа в аккаунт',
    )
    last_login = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Последний вход',
        help_text='Последний вход в аккаунт',
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата регистрации',
        help_text='Дата регистрации пользователя',
    )

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        """Возвращает строковое представление."""
        return self.name
