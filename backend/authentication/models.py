from django.db import models

from users.constants import EMAIL_LENGTH, PASSWORD_LENGTH

from .constants import PURPOSE_LENGTH


class EmailCode(models.Model):
    """Одноразовый код подтверждения (регистрация / вход / сброс пароля)."""

    class Purpose(models.TextChoices):
        REGISTRATION = ('registration', 'Регистрация')
        LOGIN = ('login', 'Вход')
        PASSWORD_RESET = ('password_reset', 'Сброс пароля')

    email = models.EmailField(
        max_length=EMAIL_LENGTH,
        verbose_name='Электронная почта',
    )
    code_hash = models.CharField(
        max_length=PASSWORD_LENGTH,
        verbose_name='Хэш кода',
    )
    purpose = models.CharField(
        max_length=PURPOSE_LENGTH,
        choices=Purpose.choices,
        verbose_name='Назначение',
    )
    attempts = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Попытки ввода',
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name='Использован',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создан',
    )
    expires_at = models.DateTimeField(
        verbose_name='Истекает',
    )

    class Meta:
        verbose_name = 'код подтверждения'
        verbose_name_plural = 'Коды подтверждения'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['email', 'purpose']),
        ]

    def __str__(self):
        """Возвращает строковое представление."""
        return f'{self.email} ({self.get_purpose_display()})'
