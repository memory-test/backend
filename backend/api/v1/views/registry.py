from dataclasses import dataclass
from typing import Type
from rest_framework.serializers import Serializer
from .services import AbstractExerciseService, ChoiceExerciseService
from .serializers import ChoiceExerciseSerializer
from backend.exercises.models import ExerciseType

@dataclass
class ExerciseConfig:
    service: AbstractExerciseService
    serializer_class: Type[Serializer]

# Единая точка расширения проекта. Добавился новый тип задания? Просто допишите строку сюда.
EXERCISE_REGISTRY = {
    ExerciseType.CHOICE: ExerciseConfig(
        service=ChoiceExerciseService(),
        serializer_class=ChoiceExerciseSerializer
    ),
}