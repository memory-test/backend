from django.contrib import admin

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
    extra = 1
    min_num = 1
    validate_min = True


class ChoiceAnswerInline(admin.TabularInline):
    model = ChoiceAnswer


class InputAnswerInline(admin.TabularInline):
    model = InputAnswer
    # max_num = 1
    # validate_max = True


class OrderingAnswerInline(admin.TabularInline):
    model = OrderingAnswer


class GroupingAnswerInline(admin.TabularInline):
    model = GroupingAnswer


class MatchingAnswerInline(admin.TabularInline):
    model = MatchingAnswer


class DrawingAnswerInline(admin.TabularInline):
    model = DrawingAnswer


@admin.register(ExerciseType)
class ExerciseTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

    fields = (('name', 'slug'), 'description')


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'type',
        'difficulty',
        'is_active',
        'created_at',
    )
    list_editable = ('difficulty', 'is_active')
    search_fields = ('title',)
    list_filter = ('type', 'difficulty', 'is_active', 'created_at')

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

    def get_inlines(
        self, request, obj: Exercise | None = None
    ) -> list[admin.TabularInline]:
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
