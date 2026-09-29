"""Тесты grouping: распределение элементов по категориям."""

import pytest
from conftest import ALL_RIGHT_ANSWER, HALF_CORRECT_ANSWER

from exercises.models import GroupingAnswer

pytestmark = pytest.mark.django_db


def test_all_assignments_correct_succeeds(
    fruits_vegetables_exercise, pass_exercise
):
    """Все элементы отнесены к верной категории — success=True, score=100."""
    exercise, apple, pear, carrot, potato = fruits_vegetables_exercise

    resp = pass_exercise(
        exercise.id,
        assignments=[
            {'item_id': apple.id, 'group': 'Фрукты'},
            {'item_id': pear.id, 'group': 'Фрукты'},
            {'item_id': carrot.id, 'group': 'Овощи'},
            {'item_id': potato.id, 'group': 'Овощи'},
        ],
    )

    assert resp.status_code == 200
    assert resp.data['score'] == ALL_RIGHT_ANSWER
    assert resp.data['success'] is True


def test_partial_assignments_correct_scores_proportionally(
    fruits_vegetables_exercise, pass_exercise
):
    """Половина элементов отнесена неверно — score считается по доле верных."""
    exercise, apple, pear, carrot, potato = fruits_vegetables_exercise

    resp = pass_exercise(
        exercise.id,
        assignments=[
            {'item_id': apple.id, 'group': 'Фрукты'},
            {'item_id': pear.id, 'group': 'Овощи'},
            {'item_id': carrot.id, 'group': 'Овощи'},
            {'item_id': potato.id, 'group': 'Фрукты'},
        ],
    )

    assert resp.status_code == 200
    assert resp.data['score'] == HALF_CORRECT_ANSWER
    assert resp.data['success'] is False


def test_foreign_item_id_rejected(make_exercise, pass_exercise):
    """Id элемента из другого задания отклоняется с 400."""

    exercise = make_exercise('grouping', 'Задание А')
    other_exercise = make_exercise('grouping', 'Задание Б')
    foreign = GroupingAnswer.objects.create(
        exercise=other_exercise, text='Чужой элемент', group='Категория'
    )

    resp = pass_exercise(
        exercise.id,
        assignments=[{'item_id': foreign.id, 'group': 'Категория'}],
    )

    assert resp.status_code == 400
    assert 'assignments' in resp.data


def test_malformed_assignment_rejected(
    fruits_vegetables_exercise, pass_exercise
):
    """Назначение без обязательного поля group отклоняется с 400."""
    exercise, apple, _, _, _ = fruits_vegetables_exercise

    resp = pass_exercise(exercise.id, assignments=[{'item_id': apple.id}])

    assert resp.status_code == 400
    assert 'assignments' in resp.data
