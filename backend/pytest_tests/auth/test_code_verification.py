"""Тесты подтверждения кода: регистрация, вход, повтор, срок действия."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from .conftest import CODE_REQUEST, VERIFY
from authentication.models import EmailCode

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_verify_registration_activates_and_returns_jwt(
    register_and_code, post
):
    """Верный код регистрации активирует пользователя и выдаёт JWT."""
    _, code = register_and_code()

    resp = post(
        VERIFY,
        {'email': 'alice@example.com', 'code': code, 'purpose': 'registration'},
    )

    assert resp.status_code == 200
    assert 'access' in resp.data
    assert 'refresh' in resp.data
    assert User.objects.get(email='alice@example.com').is_active is True


def test_verify_wrong_code(register, post):
    """Неверный код отклоняется."""
    register()

    resp = post(
        VERIFY,
        {
            'email': 'alice@example.com',
            'code': '000000',
            'purpose': 'registration',
        },
    )

    assert resp.status_code == 400


def test_verify_reuse_code_rejected(register_and_code, post):
    """Один и тот же код нельзя использовать повторно."""
    _, code = register_and_code()
    payload = {
        'email': 'alice@example.com',
        'code': code,
        'purpose': 'registration',
    }

    first = post(VERIFY, payload)
    second = post(VERIFY, payload)

    assert first.status_code == 200
    assert second.status_code == 400


def test_verify_expired_code_rejected(register_and_code, post):
    """Просроченный код отклоняется."""
    _, code = register_and_code()
    code_obj = EmailCode.objects.filter(
        email='alice@example.com', purpose='registration'
    ).latest('created_at')
    code_obj.expires_at = timezone.now() - timedelta(minutes=1)
    code_obj.save()

    resp = post(
        VERIFY,
        {'email': 'alice@example.com', 'code': code, 'purpose': 'registration'},
    )

    assert resp.status_code == 400


def test_code_login_returns_jwt(active_user, post, last_code):
    """Вход по одноразовому коду выдаёт JWT активному пользователю."""
    active_user(email='frank@example.com')
    post(CODE_REQUEST, {'email': 'frank@example.com'})
    code = last_code()

    resp = post(
        VERIFY,
        {'email': 'frank@example.com', 'code': code, 'purpose': 'login'},
    )

    assert resp.status_code == 200
    assert 'access' in resp.data