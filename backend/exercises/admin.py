from django.contrib import admin

from exercises.models import Exercise, ExerciseType


@admin.register(ExerciseType)
class ExerciseTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

    fields = ('name', 'description')


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'type__name',
        'difficulty',
        'is_active',
        'created_at',
    )
    list_editable = ('difficulty', 'is_active')
    search_fields = ('title',)
    list_filter = ('type__name', 'difficulty', 'is_active', 'created_at')

    readonly_fields = ('created_at',)
    fieldsets = (
        (
            'Oсновная информация',
            {
                'fields': (
                    'title',
                    'description',
                    'type',
                    'difficulty',
                    'config',
                ),
            },
        ),
        (
            'Дoполнительная информация',
            {
                'fields': (('is_active', 'created_at')),
            },
        ),
    )
