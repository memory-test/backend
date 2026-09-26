from django.contrib import admin

from authentication.models import EmailCode


@admin.register(EmailCode)
class EmailCodeAdmin(admin.ModelAdmin):
    """Коды подтверждения в админке (только просмотр)."""

    list_display = (
        'email',
        'purpose',
        'is_used',
        'attempts',
        'created_at',
        'expires_at',
    )
    list_filter = (
        'purpose',
        'is_used',
    )
    search_fields = ('email',)
    ordering = ('-created_at',)
    readonly_fields = (
        'email',
        'code_hash',
        'purpose',
        'attempts',
        'is_used',
        'created_at',
        'expires_at',
    )

    def has_add_permission(self, request):
        """Запрещает создание кодов подтверждения вручную."""
        return False
