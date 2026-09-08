from abc import ABC, abstractmethod
from dataclasses import dataclass

from django.shortcuts import get_object_or_404

from exercises.models import Exercise


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Универсальный дата класс для возврата результатов проверки"""
    score: float
    success: bool

class AbstractExerciseService(ABC):
    """Интерфейс для работы с заданиями."""


    @abstractmethod
    def get_exercise(self, exercise_id: int) -> Exercise:
        """
        Принимает ID задания, достает его из БД и формирует
        словарь для начала выполнения задания.
        """
        ...

    @abstractmethod
    def check_answer(self, exercise: Exercise, user_answer_data: dict) -> EvaluationResult:
        """
        Полная проверка результатов задания.
        Сравнивает ответ пользователя с эталоном из БД.
        """
        ...



class ChooseExerciseService(AbstractExerciseService):

    def get_exercise(self, exercise_id: int) -> Exercise:
        return get_object_or_404(Exercise.objects.prefetch_related('choiceanswers'), id=exercise_id)

    def check_answer(self, exercise: Exercise, user_answer_data: dict) -> EvaluationResult:
        correct_options = [
            answer.id for answer in exercise.choiceanswers.all() if answer.is_correct
        ]
        user_choices: list = user_answer_data.get('answers_ids')
        success = sorted(user_choices) == sorted(correct_options)
        # TODO: Релизовать алгоритм вычисления баллов за выполнения задания,
        #  для этого нужна будет формула.
        score = 100 if success else 0
        return EvaluationResult(success=success, score=score)