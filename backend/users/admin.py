from django.contrib import admin

from .models import User

admin.site.empty_value_display = 'Не задано'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
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
    ordering = ('-created_at',)
