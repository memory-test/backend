import difflib
import re
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass

from django.shortcuts import get_object_or_404

from exercises.models import Exercise, InputAnswer


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
    def check_answer(
        self, exercise: Exercise, user_answer_data: dict
    ) -> EvaluationResult:
        """
        Полная проверка результатов задания.
        Сравнивает ответ пользователя с эталоном из БД.
        """
        ...


class ChooseExerciseService(AbstractExerciseService):
    def get_exercise(self, exercise_id: int) -> Exercise:
        return get_object_or_404(
            Exercise.objects.prefetch_related('choiceanswers'), id=exercise_id
        )

    def check_answer(
        self, exercise: Exercise, user_answer_data: dict
    ) -> EvaluationResult:
        correct_options = [
            answer.id
            for answer in exercise.choiceanswers.all()
            if answer.is_correct
        ]
        user_choices: list = user_answer_data.get('answers_ids')
        success = sorted(user_choices) == sorted(correct_options)
        # TODO: Релизовать алгоритм вычисления баллов за выполнения задания,
        #  для этого нужна будет формула.
        score = 100 if success else 0
        return EvaluationResult(success=success, score=score)


class InputExerciseService(AbstractExerciseService):
    """Тип input: один ответ, список слов или свободная форма."""

    FREE_SUCCESS_THRESHOLD = 60

    _STOP_WORDS = frozenset(
        {
            'и',
            'а',
            'но',
            'не',
            'что',
            'как',
            'это',
            'то',
            'в',
            'на',
            'с',
            'по',
            'для',
            'из',
            'к',
            'у',
            'о',
            'от',
            'до',
            'же',
            'бы',
            'ли',
        }
    )

    def get_exercise(self, exercise_id: int) -> Exercise:
        """Достаёт задание вместе с эталонным ответом."""
        return get_object_or_404(
            Exercise.objects.prefetch_related('inputanswers'), id=exercise_id
        )

    def check_answer(
        self, exercise: Exercise, user_answer_data: dict
    ) -> EvaluationResult:
        """Выбирает способ проверки по check_method эталона."""
        answers = list(exercise.inputanswers.all())
        user_items = user_answer_data.get('answers', [])
        method = answers[0].check_method

        if method == InputAnswer.CheckMethod.SINGLE_ANSWER:
            return self._check_single(answers, user_items)
        if method == InputAnswer.CheckMethod.LIST_ANSWER:
            return self._check_list(answers, user_items)
        return self._check_free(answers, user_items)

    def _check_single(self, answers, user_items) -> EvaluationResult:
        """Сравнивает единственный ответ с эталоном."""
        expected = self._normalize(answers[0].expected_text)
        success = self._normalize(user_items[0]) == expected
        return EvaluationResult(success=success, score=100 if success else 0)

    def _check_list(self, answers, user_items) -> EvaluationResult:
        """Считает долю угаданных слов от общего числа эталонных."""
        expected = {
            self._normalize(el)
            for el in self._split_words(answers[0].expected_text)
        }
        if not expected:
            return EvaluationResult(success=False, score=0)

        user_words = []
        for item in user_items:
            user_words.extend(self._split_words(item))
        user_set = {self._normalize(w) for w in user_words}

        matched = len(expected & user_set)
        score = round(matched / len(expected) * 100, 2)
        return EvaluationResult(success=matched == len(expected), score=score)

    def _check_free(self, answers, user_items) -> EvaluationResult:
        """Приблизительная оценка по доле совпадающих слов с эталоном,
        без учёта коротких служебных слов."""
        expected_words = self._drop_stop_words(
            [
                self._normalize(el)
                for el in self._split_words(answers[0].expected_text)
            ]
        )
        user_words = self._drop_stop_words(
            [self._normalize(w) for w in self._split_words(user_items[0])]
        )
        if not expected_words or not user_words:
            return EvaluationResult(success=False, score=0)

        ratio = difflib.SequenceMatcher(
            None, expected_words, user_words
        ).ratio()
        score = round(ratio * 100, 2)
        return EvaluationResult(
            success=score >= self.FREE_SUCCESS_THRESHOLD, score=score
        )

    @classmethod
    def _drop_stop_words(cls, words: list[str]) -> list[str]:
        """Убирает короткие служебные слова, чтобы они не завышали
        схожесть между несвязанными по смыслу ответами."""
        return [w for w in words if w not in cls._STOP_WORDS]

    @staticmethod
    def _split_words(raw: str) -> list[str]:
        """Режет строку на слова по запятым и/или пробелам."""
        if not raw:
            return []
        return [part for part in re.split(r'[,\s]+', raw.strip()) if part]

    @staticmethod
    def _normalize(value: str) -> str:
        """Убирает регистр и пунктуацию для сравнения слова."""
        if not value:
            return ''
        value = unicodedata.normalize('NFKC', value)
        value = value.strip().lower()
        return re.sub(r'[^\w]', '', value, flags=re.UNICODE)


class MatchingExerciseService(AbstractExerciseService):
    """Тип matching: сопоставление пар (текстовые карточки)."""

    def get_exercise(self, exercise_id: int) -> Exercise:
        return get_object_or_404(
            Exercise.objects.prefetch_related('matchinganswers'),
            id=exercise_id,
        )

    def check_answer(
        self, exercise: Exercise, user_answer_data: dict
    ) -> EvaluationResult:
        total = exercise.matchinganswers.count()
        if not total:
            return EvaluationResult(success=False, score=0)

        submitted_pairs = user_answer_data.get('pairs', [])
        correct_ids = {
            p['first_id']
            for p in submitted_pairs
            if p['first_id'] == p['second_id']
        }
        score = round(len(correct_ids) / total * 100, 2)
        return EvaluationResult(success=len(correct_ids) == total, score=score)
