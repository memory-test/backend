"""Тесты matching: сопоставление пар."""

import pytest

from exercises.models import MatchingAnswer

pytestmark = pytest.mark.django_db


def test_all_pairs_correct_succeeds(two_pairs_exercise, pass_exercise):
    """Все пары совпадают по id — success=True, score=100."""
    exercise, pair_one, pair_two = two_pairs_exercise

    resp = pass_exercise(
        exercise.id,
        pairs=[
            {'first_id': pair_one.id, 'second_id': pair_one.id},
            {'first_id': pair_two.id, 'second_id': pair_two.id},
        ],
    )

    assert resp.status_code == 200
    assert resp.data['score'] == 100
    assert resp.data['success'] is True


def test_partial_pairs_correct_scores_proportionally(
    two_pairs_exercise, pass_exercise
):
    """Часть пар перепутана — score считается по доле верных."""
    exercise, pair_one, pair_two = two_pairs_exercise

    resp = pass_exercise(
        exercise.id,
        pairs=[
            {'first_id': pair_one.id, 'second_id': pair_one.id},
            {'first_id': pair_two.id, 'second_id': pair_one.id},
        ],
    )

    assert resp.status_code == 200
    assert resp.data['score'] == 50.0
    assert resp.data['success'] is False


def test_foreign_pair_id_rejected(make_exercise, pass_exercise):
    """Id карточки из другого задания отклоняется с 400."""
    exercise = make_exercise('matching', 'Задание А')
    other_exercise = make_exercise('matching', 'Задание Б')
    foreign = MatchingAnswer.objects.create(
        exercise=other_exercise, first_text='Чужой', second_text='Чужой'
    )

    resp = pass_exercise(
        exercise.id,
        pairs=[{'first_id': foreign.id, 'second_id': foreign.id}],
    )

    assert resp.status_code == 400
    assert 'pairs' in resp.data
