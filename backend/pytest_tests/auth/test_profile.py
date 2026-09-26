"""Тесты профиля пользователя (djoser me): доступ, возраст, прогресс,
read-only поля."""

from datetime import date
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from .conftest import ME

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_me_requires_auth(api_client):
    """Профиль недоступен без авторизации."""
    resp = api_client.get(f'/api/v1{ME}')

    assert resp.status_code == 401


def test_me_returns_profile(active_user, auth, api_client):
    """Профиль возвращает данные текущего пользователя."""
    active_user()
    auth('carol@example.com', 'Str0ng-Passw0rd-2026')

    resp = api_client.get(f'/api/v1{ME}')

    assert resp.status_code == 200
    assert resp.data['email'] == 'carol@example.com'


@patch('authentication.djoser.timezone.localdate')
def test_me_returns_age(localdate_mock, active_user, auth, api_client):
    """Возраст считается по дате рождения на текущую дату."""
    localdate_mock.return_value = date(2026, 9, 16)
    user = active_user()
    user.birth_date = date(1990, 1, 1)
    user.save(update_fields=['birth_date'])
    auth('carol@example.com', 'Str0ng-Passw0rd-2026')

    resp = api_client.get(f'/api/v1{ME}')

    assert resp.data['age'] == 36


def test_me_returns_null_age_without_birth_date(active_user, auth, api_client):
    """Без даты рождения возраст возвращается как null."""
    active_user()
    auth('carol@example.com', 'Str0ng-Passw0rd-2026')

    resp = api_client.get(f'/api/v1{ME}')

    assert resp.data['age'] is None


@patch('authentication.djoser.timezone.localdate')
def test_me_age_before_and_after_birthday(
    localdate_mock, active_user, auth, api_client
):
    """Возраст корректно меняется до и после дня рождения в текущем году."""
    localdate_mock.return_value = date(2026, 9, 16)
    user = active_user()
    auth('carol@example.com', 'Str0ng-Passw0rd-2026')

    user.birth_date = date(2000, 9, 17)
    user.save(update_fields=['birth_date'])
    resp = api_client.get(f'/api/v1{ME}')
    assert resp.data['age'] == 25

    user.birth_date = date(2000, 9, 15)
    user.save(update_fields=['birth_date'])
    resp = api_client.get(f'/api/v1{ME}')
    assert resp.data['age'] == 26


def test_me_progress_is_zero_without_active_exercises(
    active_user, auth, api_client
):
    """Прогресс равен нулю, если нет пройденных активных заданий."""
    active_user()
    auth('carol@example.com', 'Str0ng-Passw0rd-2026')

    resp = api_client.get(f'/api/v1{ME}')

    assert resp.data['progress_percent'] == 0


def test_me_progress_for_completed_active_exercises(
    active_user, auth, api_client, make_offline_exercise, make_session
):
    """Прогресс — доля пройденных активных заданий от их общего числа."""
    user = active_user()
    exercises = [
        make_offline_exercise(f'Задание {index}') for index in range(4)
    ]
    make_session(user, exercises[0])
    auth('carol@example.com', 'Str0ng-Passw0rd-2026')

    resp = api_client.get(f'/api/v1{ME}')

    assert resp.data['progress_percent'] == 25


def test_me_progress_rounds_to_two_decimal_places(
    active_user, auth, api_client, make_offline_exercise, make_session
):
    """Прогресс округляется до двух знаков после запятой."""
    user = active_user()
    exercises = [
        make_offline_exercise(f'Задание {index}') for index in range(3)
    ]
    make_session(user, exercises[0])
    auth('carol@example.com', 'Str0ng-Passw0rd-2026')

    resp = api_client.get(f'/api/v1{ME}')

    assert resp.data['progress_percent'] == 33.33


def test_me_progress_counts_repeated_exercise_once(
    active_user, auth, api_client, make_offline_exercise, make_session
):
    """Повторное прохождение одного задания засчитывается один раз."""
    user = active_user()
    completed_exercise = make_offline_exercise('Пройденное задание')
    make_offline_exercise('Непройденное задание')
    make_session(user, completed_exercise)
    make_session(user, completed_exercise)
    auth('carol@example.com', 'Str0ng-Passw0rd-2026')

    resp = api_client.get(f'/api/v1{ME}')

    assert resp.data['progress_percent'] == 50


def test_me_progress_counts_unsuccessful_session(
    active_user, auth, api_client, make_offline_exercise, make_session
):
    """Неуспешная попытка всё равно засчитывается как прохождение
    для прогресса."""
    user = active_user()
    exercise = make_offline_exercise('Неуспешно пройденное задание')
    make_session(user, exercise, success=False)
    auth('carol@example.com', 'Str0ng-Passw0rd-2026')

    resp = api_client.get(f'/api/v1{ME}')

    assert resp.data['progress_percent'] == 100


def test_me_progress_ignores_inactive_exercises(
    active_user, auth, api_client, make_offline_exercise, make_session
):
    """Неактивные задания не учитываются в прогрессе."""
    user = active_user()
    make_offline_exercise('Активное задание')
    inactive_exercise = make_offline_exercise(
        'Неактивное задание', is_active=False
    )
    make_session(user, inactive_exercise)
    auth('carol@example.com', 'Str0ng-Passw0rd-2026')

    resp = api_client.get(f'/api/v1{ME}')

    assert resp.data['progress_percent'] == 0


def test_me_role_is_read_only(active_user, auth, api_client):
    """Роль нельзя изменить через профиль."""
    active_user()
    auth('carol@example.com', 'Str0ng-Passw0rd-2026')

    resp = api_client.patch(f'/api/v1{ME}', {'role': 'admin'}, format='json')

    assert resp.status_code == 200
    assert User.objects.get(email='carol@example.com').role == 'user'


def test_me_patch_updates_profile_fields(active_user, auth, api_client):
    """PATCH обновляет разрешённые поля и возвращает полный профиль,
    а не только изменённые поля."""
    active_user()
    auth('carol@example.com', 'Str0ng-Passw0rd-2026')

    resp = api_client.patch(
        f'/api/v1{ME}',
        {
            'name': 'Carol Updated',
            'birth_date': '1995-03-01',
            'current_difficulty': 'hard',
        },
        format='json',
    )

    assert resp.status_code == 200
    user = User.objects.get(email='carol@example.com')
    assert user.name == 'Carol Updated'
    assert str(user.birth_date) == '1995-03-01'
    assert user.current_difficulty == 'hard'
    assert resp.data['email'] == 'carol@example.com'
    assert 'date_joined' in resp.data


def test_me_patch_ignores_read_only_fields(active_user, auth, api_client):
    """PATCH молча игнорирует попытку изменить read-only поля
    (email, role, age, progress_percent)."""
    active_user()
    auth('carol@example.com', 'Str0ng-Passw0rd-2026')

    resp = api_client.patch(
        f'/api/v1{ME}',
        {
            'email': 'hacker@example.com',
            'role': 'admin',
            'age': 99,
            'progress_percent': 100,
        },
        format='json',
    )

    assert resp.status_code == 200
    user = User.objects.get(email='carol@example.com')
    assert user.email == 'carol@example.com'
    assert user.role == 'user'
    assert resp.data['age'] is None
    assert resp.data['progress_percent'] == 0