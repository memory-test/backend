"""Тесты input с check_method=list_answer."""

import pytest

pytestmark = pytest.mark.django_db


def test_all_words_correct_succeeds(four_words_exercise, pass_exercise):
    """Все слова угаданы, порядок и регистр не важны."""
    resp = pass_exercise(
        four_words_exercise.id, answers=['лампа', 'СТОЛ', 'дверь', 'окно']
    )

    assert resp.status_code == 200
    assert resp.data['score'] == 100
    assert resp.data['success'] is True


def test_partial_match_scores_proportionally(
    four_words_exercise, pass_exercise
):
    """Доля угаданных слов пересчитывается в проценты."""
    resp = pass_exercise(
        four_words_exercise.id, answers=['стол', 'окно', 'дверь']
    )

    assert resp.status_code == 200
    assert resp.data['score'] == 75.0
    assert resp.data['success'] is False
