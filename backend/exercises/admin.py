from django.contrib import admin
from django.forms import BaseInlineFormSet
from .models import ChoiceExercise, ChoiceOption


class ChoiceOptionFormSet(BaseInlineFormSet):
    # TODO: написать валидатор для проверки вариантов ответов.


class ChoiceOptionInline(admin.TabularInline):
    """
    Описывает отображение вариантов ответов внутри карточки задания.
    """
    model = ChoiceOption
    formset = ChoiceOptionFormSet
    extra = 4
    min_num = 2
    fields = ('text', 'is_correct')

@admin.register(ChoiceExercise)
class ChoiceExerciseAdmin(admin.ModelAdmin):
    list_display = ('title', 'difficulty', 'is_multiple', 'is_active', 'created_at')
    list_filter = ('difficulty', 'is_multiple', 'is_active', 'created_at')
    search_fields = ('title', 'description')
    # админ сможет удобно добавлять варианты ответов к заданию.
    inlines = [ChoiceOptionInline]


