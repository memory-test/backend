"""Тесты рейт-лимита на запрос одноразового кода."""

import pytest

from .conftest import CODE_REQUEST

pytestmark = pytest.mark.django_db


def test_code_request_cooldown(active_user, post):
    """Повторный запрос кода до истечения кулдауна отклоняется 429."""
    active_user(email='eve@example.com')

    first = post(CODE_REQUEST, {'email': 'eve@example.com'})
    second = post(CODE_REQUEST, {'email': 'eve@example.com'})

    assert first.status_code == 200
    assert second.status_code == 429