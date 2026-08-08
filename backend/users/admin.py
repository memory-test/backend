from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User

admin.site.empty_value_display = 'Не задано'


@admin.register(User)
class UserAdmin(UserAdmin):
    """Модель пользователя в админке."""

    list_display = (
        'username',
        'email',
    )
    list_filter = ('username',)
    search_fields = (
        'username',
        'email',
    )
    ordering = ('username',)
