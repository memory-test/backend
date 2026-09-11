from django_filters import rest_framework as filters

from exercises.models import Exercise, ExerciseType
from users.models import Difficulty


class ExerciseFilter(filters.FilterSet):
    """Фильтр для эндпоинтов Заданий."""

    type = filters.ChoiceFilter(choices=ExerciseType.choices)
    difficulty = filters.ChoiceFilter(choices=Difficulty.choices)

    class Meta:
        model = Exercise
        fields = ('type', 'difficulty')
