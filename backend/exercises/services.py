import json
import re
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass

from django.conf import settings
from django.shortcuts import get_object_or_404
from openai import OpenAI, OpenAIError

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


def _normalize_answer(value: str) -> str:
    """Приводит ответ к каноническому виду: без регистра, лишних
    пробелов и пунктуации."""
    if not value:
        return ''
    value = unicodedata.normalize('NFKC', value)
    value = value.strip().lower()
    value = re.sub(r'[^\w\s]', '', value, flags=re.UNICODE)
    return re.sub(r'\s+', ' ', value)


@dataclass(frozen=True, slots=True)
class GradingResult:
    score: float  # 0..100
    feedback: str = ''


class AnswerGrader(ABC):
    """Интерфейс LLM-проверки свободного ответа по критериям."""

    @abstractmethod
    def grade(
        self, *, question: str, criteria: str, user_answer: str
    ) -> GradingResult: ...


class StubAnswerGrader(AnswerGrader):
    """Заглушка: пересечение слов ответа и критериев. Используется
    при отсутствии GROK_API_KEY или при сбое реального вызова."""

    def grade(
        self, *, question: str, criteria: str, user_answer: str
    ) -> GradingResult:
        user_words = set(_normalize_answer(user_answer).split())
        criteria_words = set(_normalize_answer(criteria).split())
        if not user_words or not criteria_words:
            return GradingResult(
                score=0.0, feedback='Пустой ответ или критерии.'
            )
        overlap = len(user_words & criteria_words) / len(criteria_words)
        return GradingResult(
            score=round(overlap * 100, 2),
            feedback='Оценено заглушкой (пересечение слов), не LLM.',
        )


_GRADING_SYSTEM_PROMPT = (
    'Ты проверяешь ответ ученика на задание тренажёра памяти. '
    'Оцени ответ по переданным критериям и верни СТРОГО JSON без '
    'какого-либо текста вокруг: {"score": <число от 0 до 100>, '
    '"feedback": "<краткий комментарий на русском>"}.'
)


class GroqAnswerGrader(AnswerGrader):
    """
    LLM-проверка через Groq (OpenAI-совместимый API, llama-3.3-70b-versatile).
    """

    def __init__(self):
        self._client = OpenAI(
            api_key=settings.GROK_API_KEY, base_url=settings.GROK_BASE_URL
        )

    def grade(
        self, *, question: str, criteria: str, user_answer: str
    ) -> GradingResult:
        user_prompt = (
            f'Вопрос задания: {question}\n'
            f'Критерии оценки: {criteria}\n'
            f'Ответ ученика: {user_answer}'
        )
        try:
            response = self._client.chat.completions.create(
                model=settings.GROK_MODEL,
                messages=[
                    {'role': 'system', 'content': _GRADING_SYSTEM_PROMPT},
                    {'role': 'user', 'content': user_prompt},
                ],
                temperature=0,
                response_format={'type': 'json_object'},
            )
            payload = json.loads(response.choices[0].message.content)
            score = float(payload['score'])
            return GradingResult(
                score=max(0.0, min(100.0, score)),
                feedback=str(payload.get('feedback', '')),
            )
        except (OpenAIError, KeyError, ValueError, json.JSONDecodeError):
            return StubAnswerGrader().grade(
                question=question, criteria=criteria, user_answer=user_answer
            )


class InputExerciseService(AbstractExerciseService):
    """Тип input: короткий ответ, список ответов или LLM-проверка.

    Метод проверки берётся из InputAnswer.check_method (общий для
    всех строк одного задания).
    """

    LLM_SUCCESS_THRESHOLD = 60
    DEFAULT_GRADER: AnswerGrader = (
        GroqAnswerGrader() if settings.GROK_API_KEY else StubAnswerGrader()
    )

    def get_exercise(self, exercise_id: int) -> Exercise:
        return get_object_or_404(
            Exercise.objects.prefetch_related('inputanswers'), id=exercise_id
        )

    def check_answer(
        self, exercise: Exercise, user_answer_data: dict
    ) -> EvaluationResult:
        answers = list(exercise.inputanswers.all())
        if not answers:
            return EvaluationResult(success=False, score=0)

        user_items = [a for a in user_answer_data.get('answers', []) if a]
        if not user_items:
            return EvaluationResult(success=False, score=0)

        if answers[0].check_method == InputAnswer.CheckMethod.LLM:
            return self._check_llm(exercise, answers[0], user_items)
        return self._check_exact(answers, user_items)

    def _check_exact(self, answers, user_items) -> EvaluationResult:
        expected = {_normalize_answer(a.expected_text) for a in answers}
        user_set = {_normalize_answer(a) for a in user_items}
        matched = len(expected & user_set)
        score = round(matched / len(expected) * 100, 2)
        return EvaluationResult(success=matched == len(expected), score=score)

    def _check_llm(self, exercise, answer, user_items) -> EvaluationResult:
        result = self.DEFAULT_GRADER.grade(
            question=exercise.question,
            criteria=answer.expected_text,
            user_answer=' '.join(user_items),
        )
        return EvaluationResult(
            success=result.score >= self.LLM_SUCCESS_THRESHOLD,
            score=result.score,
        )
