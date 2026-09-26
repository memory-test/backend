"""Тесты входа по паролю и обновления JWT."""

import pytest

from .conftest import REFRESH, TOKEN

pytestmark = pytest.mark.django_db


def test_token_login_by_password(active_user, post):
    """Вход по паролю выдаёт JWT."""
    active_user()

    resp = post(TOKEN, {'email': 'carol@example.com', 'password': 'Str0ng-Passw0rd-2026'})

    assert resp.status_code == 200
    assert 'access' in resp.data


def test_token_login_wrong_password(active_user, post):
    """Неверный пароль отклоняется."""
    active_user()

    resp = post(TOKEN, {'email': 'carol@example.com', 'password': 'wrong'})

    assert resp.status_code == 401


def test_token_refresh(active_user, post):
    """Refresh-токен выдаёт новый access-токен."""
    active_user(email='gina@example.com')
    tok = post(TOKEN, {'email': 'gina@example.com', 'password': 'Str0ng-Passw0rd-2026'})

    resp = post(REFRESH, {'refresh': tok.data['refresh']})

    assert resp.status_code == 200
    assert 'access' in resp.data