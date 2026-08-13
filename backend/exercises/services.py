from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EvaluationResult:
    """Универсальный дата класс для возврата результатов проверки"""
    is_correct: bool
    score: float
    success: bool

class AbstractExerciseService(ABC):
    """Интерфейс для работы с заданиями."""

    @abstractmethod
    def get_exercise_content(self, exercise_id: int) -> dict:
        """
        Принимает ID задания, достает его из БД и формирует
        словарь для начала выполнения задания.
        """
        ...

    @abstractmethod
    def check_answer(self, exercise_id: int, user_answer_data: dict) -> EvaluationResult:
        """
        Полная проверка результатов задания.
        Сравнивает ответ пользователя с эталоном из БД.
        """
        ...


class ChooseExerciseService(AbstractExerciseService):

    def get_exercise_content(self, exercise_id: int) -> dict:
        pass

    def check_answer(self, exercise_id: int, user_answer_data: dict) -> EvaluationResult:
        pass

