"""Тесты смены email (djoser set_email)."""

import pytest

from .conftest import SET_EMAIL, TOKEN

pytestmark = pytest.mark.django_db


def test_set_email_changes_login(active_user, auth, post):
    """Смена email меняет и логин для последующего входа."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    active_user()
    auth('carol@example.com', 'Str0ng-Passw0rd-2026')

    resp = post(
        SET_EMAIL,
        {
            'current_password': 'Str0ng-Passw0rd-2026',
            'new_email': 'carol-new@example.com',
        },
    )

    assert resp.status_code == 204
    assert User.objects.filter(email='carol-new@example.com').exists()

    resp = post(
        TOKEN,
        {'email': 'carol-new@example.com', 'password': 'Str0ng-Passw0rd-2026'},
    )
    assert resp.status_code == 200
    assert 'access' in resp.data


def test_set_email_wrong_current_password(active_user, auth, post):
    """Смена email требует верный текущий пароль."""
    active_user()
    auth('carol@example.com', 'Str0ng-Passw0rd-2026')

    resp = post(
        SET_EMAIL,
        {'current_password': 'wrong', 'new_email': 'carol-new@example.com'},
    )

    assert resp.status_code == 400