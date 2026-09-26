from dataclasses import dataclass
from typing import Type

from rest_framework.serializers import Serializer

import api.v1.serializers as serializers
import exercises.services as services
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
    ExerciseType.INPUT: ExerciseConfig(
        service=services.InputExerciseService(),
        write_serializer=serializers.InputCheckSerializer,
    ),
    ExerciseType.MATCHING: ExerciseConfig(
        service=services.MatchingExerciseService(),
        write_serializer=serializers.MatchingCheckSerializer,
    ),
}
