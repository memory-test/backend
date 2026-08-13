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
        help_text='Email, на который отправлен код',
    )
    code_hash = models.CharField(
        max_length=PASSWORD_LENGTH,
        verbose_name='Хэш кода',
        help_text='Хэш одноразового кода (открыто не хранится)',
    )
    purpose = models.CharField(
        max_length=PURPOSE_LENGTH,
        choices=Purpose.choices,
        verbose_name='Назначение',
        help_text='Для чего отправлен код',
    )
    attempts = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Попытки ввода',
        help_text='Количество неверных вводов кода',
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name='Использован',
        help_text='Был ли код уже использован',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создан',
        help_text='Дата и время создания кода',
    )
    expires_at = models.DateTimeField(
        verbose_name='Истекает',
        help_text='Дата и время окончания действия кода',
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
