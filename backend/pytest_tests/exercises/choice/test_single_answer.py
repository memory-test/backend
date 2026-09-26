"""Тесты choice с выбором одного правильного варианта."""

import pytest

from exercises.models import ChoiceAnswer

pytestmark = pytest.mark.django_db


def test_correct_answer_succeeds(make_exercise, pass_exercise):
    """Верно выбранный вариант даёт success=True, score=100."""
    exercise = make_exercise('choice', 'Столица России')
    correct = ChoiceAnswer.objects.create(
        exercise=exercise, text='Москва', is_correct=True
    )
    ChoiceAnswer.objects.create(
        exercise=exercise, text='Казань', is_correct=False
    )

    resp = pass_exercise(exercise.id, answers_ids=[correct.id])

    assert resp.status_code == 200
    assert resp.data['score'] == 100
    assert resp.data['success'] is True


def test_wrong_answer_fails(make_exercise, pass_exercise):
    """Неверный вариант даёт success=False, score=0."""
    exercise = make_exercise('choice', 'Столица Франции')
    ChoiceAnswer.objects.create(
        exercise=exercise, text='Париж', is_correct=True
    )
    wrong = ChoiceAnswer.objects.create(
        exercise=exercise, text='Лондон', is_correct=False
    )

    resp = pass_exercise(exercise.id, answers_ids=[wrong.id])

    assert resp.status_code == 200
    assert resp.data['score'] == 0
    assert resp.data['success'] is False


def test_foreign_answer_id_rejected(make_exercise, pass_exercise):
    """Id варианта из другого задания отклоняется с 400."""
    exercise = make_exercise('choice', 'Задание А')
    other_exercise = make_exercise('choice', 'Задание Б')
    foreign = ChoiceAnswer.objects.create(
        exercise=other_exercise, text='Чужой вариант', is_correct=True
    )

    resp = pass_exercise(exercise.id, answers_ids=[foreign.id])

    assert resp.status_code == 400
    assert 'answers_ids' in resp.data