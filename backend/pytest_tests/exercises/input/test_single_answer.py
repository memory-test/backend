"""Тесты input с check_method=single_answer."""

import pytest

from exercises.models import InputAnswer

pytestmark = pytest.mark.django_db


def test_answer_is_normalized(make_exercise, pass_exercise):
    """Сравнение без учёта регистра, пробелов и пунктуации."""
    exercise = make_exercise('input', 'Столица Франции')
    InputAnswer.objects.create(
        exercise=exercise,
        check_method=InputAnswer.CheckMethod.SINGLE_ANSWER,
        expected_text='Париж',
    )

    resp = pass_exercise(exercise.id, answers=['  париж!  '])

    assert resp.status_code == 200
    assert resp.data['score'] == 100
    assert resp.data['success'] is True


def test_wrong_answer_fails(make_exercise, pass_exercise):
    """Неверный ответ даёт success=False."""
    exercise = make_exercise('input', 'Столица Франции')
    InputAnswer.objects.create(
        exercise=exercise,
        check_method=InputAnswer.CheckMethod.SINGLE_ANSWER,
        expected_text='Париж',
    )

    resp = pass_exercise(exercise.id, answers=['Лондон'])

    assert resp.status_code == 200
    assert resp.data['success'] is False


def test_multiple_values_rejected(make_exercise, pass_exercise):
    """Более одного элемента в answers даёт 400."""
    exercise = make_exercise('input', 'Столица Италии')
    InputAnswer.objects.create(
        exercise=exercise,
        check_method=InputAnswer.CheckMethod.SINGLE_ANSWER,
        expected_text='Рим',
    )

    resp = pass_exercise(exercise.id, answers=['Рим', 'Милан'])

    assert resp.status_code == 400
    assert 'answers' in resp.data