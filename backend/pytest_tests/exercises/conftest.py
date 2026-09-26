"""Общие фикстуры для тестов прохождения заданий (pass)."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from exercises.models import ChoiceAnswer, Exercise, InputAnswer, MatchingAnswer

User = get_user_model()

API = '/api/v1'


@pytest.fixture
def user(db):
    """Создаёт тестового пользователя."""
    return User.objects.create_user(
        email='learner@example.com', name='Learner', password='pass'
    )


@pytest.fixture
def api_client(user):
    """Авторизованный APIClient."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def make_exercise(db):
    """Фабрика активных заданий указанного типа."""

    def _make_exercise(type_, title):
        return Exercise.objects.create(
            title=title,
            description='Описание',
            type=type_,
            question='Вопрос',
            is_active=True,
        )

    return _make_exercise


@pytest.fixture
def pass_exercise(api_client):
    """Отправляет POST на /pass/ с обязательными полями времени."""

    def _pass_exercise(exercise_id, **payload):
        now = timezone.now()
        body = {
            'started_at': now.isoformat(),
            'finished_at': (now + timedelta(seconds=10)).isoformat(),
            'duration_seconds': 10,
            **payload,
        }
        return api_client.post(
            f'{API}/exercises/{exercise_id}/pass/', body, format='json'
        )

    return _pass_exercise


@pytest.fixture
def two_correct_exercise(make_exercise):
    """Задание choice с двумя верными и одним неверным вариантом."""
    exercise = make_exercise('choice', 'Чётные числа')
    correct_one = ChoiceAnswer.objects.create(
        exercise=exercise, text='2', is_correct=True
    )
    correct_two = ChoiceAnswer.objects.create(
        exercise=exercise, text='4', is_correct=True
    )
    wrong = ChoiceAnswer.objects.create(
        exercise=exercise, text='3', is_correct=False
    )
    return exercise, correct_one, correct_two, wrong


@pytest.fixture
def four_words_exercise(make_exercise):
    """Задание input со списком из четырёх ожидаемых слов."""
    exercise = make_exercise('input', 'Запомните слова')
    InputAnswer.objects.create(
        exercise=exercise,
        check_method=InputAnswer.CheckMethod.LIST_ANSWER,
        expected_text='Стол, Окно, Дверь, Лампа',
    )
    return exercise


@pytest.fixture
def proverb_exercise(make_exercise):
    """Задание input со свободным ответом и эталоном-рубрикой."""
    exercise = make_exercise('input', 'Смысл пословицы')
    InputAnswer.objects.create(
        exercise=exercise,
        check_method=InputAnswer.CheckMethod.FREE_ANSWER,
        expected_text='Нужно не торопиться, тогда быстрее дойдёшь до цели',
    )
    return exercise


@pytest.fixture
def two_pairs_exercise(make_exercise):
    """Задание matching с двумя парами противоположностей."""
    exercise = make_exercise('matching', 'Противоположности')
    pair_one = MatchingAnswer.objects.create(
        exercise=exercise, first_text='Горячий', second_text='Холодный'
    )
    pair_two = MatchingAnswer.objects.create(
        exercise=exercise, first_text='Большой', second_text='Маленький'
    )
    return exercise, pair_one, pair_two