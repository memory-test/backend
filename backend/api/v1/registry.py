from dataclasses import dataclass
from typing import Type
from rest_framework.serializers import Serializer
import exercises.services as services
import api.v1.serializers as serializers
from exercises.models import ExerciseType

@dataclass
class ExerciseConfig:
    service: services.AbstractExerciseService
    write_serializer: Type[Serializer]

EXERCISE_REGISTRY = {
    ExerciseType.CHOICE: ExerciseConfig(
        service=services.ChooseExerciseService(),
        write_serializer=serializers.ChoiceCheckSerializer,
    ),
}