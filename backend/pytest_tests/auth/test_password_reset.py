"""Тесты сброса пароля по коду."""

import pytest

from .conftest import RESET, RESET_CONFIRM, TOKEN

pytestmark = pytest.mark.django_db


def test_password_reset_flow(active_user, post, last_code):
    """Полный цикл сброса пароля: запрос кода, подтверждение, вход
    с новым паролем."""
    active_user(email='dave@example.com')
    resp = post(RESET, {'email': 'dave@example.com'})
    assert resp.status_code == 204

    code = last_code()
    new_pwd = 'BrandNew-Passw0rd-99'
    resp = post(
        RESET_CONFIRM,
        {'email': 'dave@example.com', 'code': code, 'new_password': new_pwd},
    )
    assert resp.status_code == 204

    resp = post(TOKEN, {'email': 'dave@example.com', 'password': new_pwd})
    assert resp.status_code == 200
    assert 'access' in resp.data


def test_password_reset_unknown_email_is_generic(post):
    """Сброс пароля для несуществующего email не выдаёт его
    отсутствие (анти-enumeration)."""
    from django.core import mail

    resp = post(RESET, {'email': 'noone@example.com'})

    assert resp.status_code == 204
    assert len(mail.outbox) == 0


def test_password_reset_confirm_weak_password_keeps_code(
    active_user, post, last_code
):
    """Слабый пароль не «сжигает» код: проверка идёт до расходования."""
    active_user(email='dave@example.com')
    post(RESET, {'email': 'dave@example.com'})
    code = last_code()

    resp = post(
        RESET_CONFIRM,
        {'email': 'dave@example.com', 'code': code, 'new_password': '123'},
    )
    assert resp.status_code == 400
    assert 'new_password' in resp.data

    resp = post(
        RESET_CONFIRM,
        {
            'email': 'dave@example.com',
            'code': code,
            'new_password': 'BrandNew-Passw0rd-99',
        },
    )
    assert resp.status_code == 204


def test_password_reset_blacklists_old_tokens(active_user, post, last_code):
    """Сброс пароля отзывает все ранее выданные токены пользователя."""
    active_user(email='dave@example.com')
    tok = post(TOKEN, {'email': 'dave@example.com', 'password': 'Str0ng-Passw0rd-2026'})
    post(RESET, {'email': 'dave@example.com'})
    code = last_code()

    resp = post(
        RESET_CONFIRM,
        {
            'email': 'dave@example.com',
            'code': code,
            'new_password': 'BrandNew-Passw0rd-99',
        },
    )
    assert resp.status_code == 204

    from .conftest import REFRESH

    refreshed = post(REFRESH, {'refresh': tok.data['refresh']})
    assert refreshed.status_code == 401