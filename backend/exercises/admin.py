from django.contrib import admin
from django.contrib.admin.options import InlineModelAdmin
from django.http import HttpRequest

from exercises.models import (
    ChoiceAnswer,
    DrawingAnswer,
    Exercise,
    ExerciseType,
    GroupingAnswer,
    InputAnswer,
    MatchingAnswer,
    OrderingAnswer,
)


class AnswerInline(admin.TabularInline):
    extra = 0
    min_num = 1
    validate_min = True


class ChoiceAnswerInline(AnswerInline):
    model = ChoiceAnswer


class InputAnswerInline(AnswerInline):
    model = InputAnswer


class OrderingAnswerInline(AnswerInline):
    model = OrderingAnswer


class GroupingAnswerInline(AnswerInline):
    model = GroupingAnswer


class MatchingAnswerInline(AnswerInline):
    model = MatchingAnswer


class DrawingAnswerInline(AnswerInline):
    model = DrawingAnswer


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = (
        'display_id',
        'title',
        'type',
        'difficulty',
        'is_active',
        'created_at',
    )
    list_editable = ('difficulty', 'is_active')
    search_fields = ('title', 'id')
    list_filter = ('type', 'difficulty', 'is_active', 'created_at')

    readonly_fields = ('display_id', 'created_at')
    fieldsets = (
        (
            'Oсновная информация',
            {
                'fields': (
                    ('display_id', 'title'),
                    'description',
                    ('type', 'difficulty'),
                    'question',
                    ('image', 'audio'),
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

    @admin.display(description='Номер', ordering='id')
    def display_id(self, obj):
        if obj.id:
            return obj.id
        return ''

    def get_inlines(
        self, request: HttpRequest, obj: Exercise | None = None
    ) -> list[type[InlineModelAdmin]]:
        if obj is None:
            return []

        if obj.type == ExerciseType.CHOICE:
            return [ChoiceAnswerInline]

        if obj.type == ExerciseType.INPUT:
            return [InputAnswerInline]

        if obj.type == ExerciseType.ORDERING:
            return [OrderingAnswerInline]

        if obj.type == ExerciseType.GROUPING:
            return [GroupingAnswerInline]

        if obj.type == ExerciseType.MATCHING:
            return [MatchingAnswerInline]

        if obj.type == ExerciseType.DRAWING:
            return [DrawingAnswerInline]

        return []
