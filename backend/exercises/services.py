from abc import ABC, abstractmethod
from dataclasses import dataclass

from django.shortcuts import get_object_or_404

from backend.exercises.models import ExerciseBase


@dataclass
class EvaluationResult:
    """Универсальный дата класс для возврата результатов проверки"""
    score: float
    success: bool

class AbstractExerciseService(ABC):
    """Интерфейс для работы с заданиями."""


    @abstractmethod
    def get_exercise(self, exercise_id: int) -> ExerciseBase:
        """
        Принимает ID задания, достает его из БД и формирует
        словарь для начала выполнения задания.
        """
        ...

    @abstractmethod
    def check_answer(self, exercise: ExerciseBase, user_answer_data: dict) -> EvaluationResult:
        """
        Полная проверка результатов задания.
        Сравнивает ответ пользователя с эталоном из БД.
        """
        ...


class ChooseExerciseService(AbstractExerciseService):

    def get_exercise(self, exercise_id: int) -> ExerciseBase:
        exercise = ExerciseBase.objects.select_related('choiceexercise').prefetch_related(
            'choiceexercise__options').get(id=exercise_id)
        return exercise
        # return get_object_or_404(
        #     ChoiceExercise.objects.select_related('exercisebase_ptr').prefetch_related('options'),
        #     id=exercise_id
        # )

    def check_answer(self, exercise: ExerciseBase, user_answer_data: dict) -> EvaluationResult:
        pass

