"""Тесты input с check_method=free_answer."""

import pytest

pytestmark = pytest.mark.django_db


def test_answer_close_to_reference_succeeds(proverb_exercise, pass_exercise):
    """Ответ, близкий к эталону, засчитывается."""
    resp = pass_exercise(
        proverb_exercise.id,
        answers=['Нужно не торопиться, тогда быстрее дойдёшь до цели'],
    )

    assert resp.status_code == 200
    assert resp.data['success'] is True


def test_off_topic_answer_fails(proverb_exercise, pass_exercise):
    """Ответ не по теме не засчитывается."""
    resp = pass_exercise(
        proverb_exercise.id, answers=['Моя любимая еда — пицца']
    )

    assert resp.status_code == 200
    assert resp.data['success'] is False
