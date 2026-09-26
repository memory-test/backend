from dataclasses import dataclass
from typing import Type

from backend.exercises.models import ExerciseType
from rest_framework.serializers import Serializer

from .serializers import ChoiceExerciseSerializer
from .services import AbstractExerciseService, ChoiceExerciseService


@dataclass
class ExerciseConfig:
    service: AbstractExerciseService
    serializer_class: Type[Serializer]


# Единая точка расширения проекта. Просто допишите строку сюда.
EXERCISE_REGISTRY = {
    ExerciseType.CHOICE: ExerciseConfig(
        service=ChoiceExerciseService(),
        serializer_class=ChoiceExerciseSerializer,
    ),
}
