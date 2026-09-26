"""Тесты choice с выбором нескольких правильных вариантов."""

import pytest

pytestmark = pytest.mark.django_db


def test_all_correct_options_selected_succeeds(
    two_correct_exercise, pass_exercise
):
    """Выбраны оба верных варианта — success=True, score=100."""
    exercise, correct_one, correct_two, _ = two_correct_exercise

    resp = pass_exercise(
        exercise.id, answers_ids=[correct_one.id, correct_two.id]
    )

    assert resp.status_code == 200
    assert resp.data['score'] == 100
    assert resp.data['success'] is True


def test_partial_selection_fails(two_correct_exercise, pass_exercise):
    """Выбран только один из двух верных вариантов — success=False."""
    exercise, correct_one, _, _ = two_correct_exercise

    resp = pass_exercise(exercise.id, answers_ids=[correct_one.id])

    assert resp.status_code == 200
    assert resp.data['success'] is False


def test_correct_plus_wrong_option_fails(two_correct_exercise, pass_exercise):
    """Верный вариант вместе с неверным — success=False."""
    exercise, correct_one, _, wrong = two_correct_exercise

    resp = pass_exercise(exercise.id, answers_ids=[correct_one.id, wrong.id])

    assert resp.status_code == 200
    assert resp.data['success'] is False
