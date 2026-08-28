from dataclasses import dataclass
from typing import Type
from rest_framework.serializers import Serializer
import backend.exercises.services as services
from .serializers import ChoiceExerciseSerializer, ChoiceCheckSerializer
from backend.exercises.models import ExerciseType

@dataclass
class ExerciseConfig:
    service: services.AbstractExerciseService
    read_serializer: Type[Serializer]
    write_serializer: Type[Serializer]

EXERCISE_REGISTRY = {
    ExerciseType.CHOICE: ExerciseConfig(
        service=services.ChooseExerciseService(),
        read_serializer=ChoiceExerciseSerializer,
        write_serializer=ChoiceCheckSerializer,
    ),
}