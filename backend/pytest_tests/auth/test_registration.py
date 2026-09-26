"""Тесты регистрации и повторной отправки кода активации."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone

from .conftest import RESEND_ACTIVATION
from authentication.models import EmailCode

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_register_creates_inactive_user_and_sends_code(register):
    """Регистрация создаёт неактивного пользователя и отправляет код."""
    resp = register()

    assert resp.status_code == 201
    assert User.objects.get(email='alice@example.com').is_active is False
    assert len(mail.outbox) == 1
    assert 'alice@example.com' in mail.outbox[0].to


def test_register_duplicate_email(register):
    """Повторная регистрация на тот же email отклоняется."""
    register()
    resp = register()

    assert resp.status_code == 400
    assert 'email' in resp.data


def test_register_weak_password(register):
    """Слабый пароль отклоняется валидацией."""
    resp = register(password='123')

    assert resp.status_code == 400
    assert 'password' in resp.data


def test_register_without_password_is_simplified(register):
    """Регистрация без пароля создаёт пользователя без пригодного
    пароля (вход только по коду)."""
    resp = register(password=None)

    assert resp.status_code == 201
    assert (
        User.objects.get(email='alice@example.com').has_usable_password()
        is False
    )


def test_resend_activation_sends_new_code(register, post):
    """Повторная отправка кода активации работает после кулдауна."""
    register()
    mail.outbox = []
    EmailCode.objects.update(
        created_at=timezone.now() - timedelta(minutes=2)
    )

    resp = post(RESEND_ACTIVATION, {'email': 'alice@example.com'})

    assert resp.status_code == 204
    assert len(mail.outbox) == 1


def test_resend_activation_for_unknown_email_is_silent(post):
    """Повторная отправка на несуществующий email ничего не делает
    (анти-enumeration), но эндпоинт всё равно отвечает 204."""
    resp = post(RESEND_ACTIVATION, {'email': 'noone@example.com'})

    assert resp.status_code == 204
    assert len(mail.outbox) == 0


def test_resend_activation_cooldown_is_silent(register, post):
    """Кулдаун не роняет эндпоинт djoser — код просто не отправляется."""
    register()
    resp = post(RESEND_ACTIVATION, {'email': 'alice@example.com'})

    assert resp.status_code == 204
    assert len(mail.outbox) == 1