from django.contrib.auth.models import AbstractUser, BaseUserManager
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


class UserManager(BaseUserManager):
    """Менеджер пользователя с входом по email."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email должен быть указан')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Кастомная модель пользователя."""

    username = None
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    objects = UserManager()

    class Role(models.TextChoices):
        """Роли пользователя."""

        USER = ('user', 'Пользователь')
        ADMIN = ('admin', 'Администратор')

    name = models.CharField(
        max_length=constants.NAME_LENGTH, verbose_name='Имя'
    )
    email = models.EmailField(
        unique=True, blank=True, null=True, verbose_name='Электронная почта'
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

    def save(self, *args, **kwargs):
        """Админ (role=ADMIN) получает is_staff автоматически."""
        if self.role == self.Role.ADMIN:
            self.is_staff = True
        super().save(*args, **kwargs)
