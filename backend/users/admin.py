from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as Admin

from .models import User

admin.site.empty_value_display = 'Не задано'


@admin.register(User)
class UserAdmin(Admin):
    """Модель пользователя в админке."""

    list_display = (
        'email',
        'name',
        'role',
        'is_active',
    )
    list_filter = (
        'role',
        'is_active',
    )
    search_fields = (
        'email',
        'name',
    )
    ordering = ('-date_joined',)
