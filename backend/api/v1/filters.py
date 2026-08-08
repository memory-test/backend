from django_filters import rest_framework as filters
from exercises.models import Exercise
from users.models import Difficulty


class ExerciseFilter(filters.FilterSet):
    """Фильтр для эндпоинтов Заданий."""

    type = filters.CharFilter(field_name='type__name', lookup_expr='iexact')
    difficulty = filters.ChoiceFilter(choices=Difficulty.choices)

    class Meta:
        model = Exercise
        fields = ('type', 'difficulty')
