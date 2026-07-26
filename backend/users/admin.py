from django.contrib import admin

from .models import User

admin.site.empty_value_display = 'Не задано'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
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
