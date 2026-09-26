"""Общие fixtures для тестов аутентификации."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from exercises.models import Exercise
from progress.models import ExerciseSession

User = get_user_model()

API = '/api/v1'
REGISTER = '/auth/users/'
VERIFY = '/auth/verify/'
CODE_REQUEST = '/auth/code/request/'
RESEND_ACTIVATION = '/auth/users/resend_activation/'
RESET = '/auth/users/reset_password/'
RESET_CONFIRM = '/auth/users/reset_password_confirm/'
TOKEN = '/auth/jwt/create/'
REFRESH = '/auth/jwt/refresh/'
ME = '/auth/users/me/'
SET_EMAIL = '/auth/users/set_email/'
PWD = 'Str0ng-Passw0rd-2026'


@pytest.fixture(autouse=True)
def locmem_email(settings):
    """Переключает бэкенд почты на locmem, чтобы письма попадали в outbox."""
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'


@pytest.fixture(autouse=True)
def clear_outbox():
    """Очищает почтовый outbox перед каждым тестом."""
    mail.outbox = []


@pytest.fixture
def api_client(db):
    """Неавторизованный APIClient."""
    return APIClient()


@pytest.fixture
def post(api_client):
    """POST-запрос к API с префиксом /api/v1."""

    def _post(path, data):
        return api_client.post(f'{API}{path}', data, format='json')

    return _post


@pytest.fixture
def last_code():
    """Достаёт код из тела последнего письма в тестовом outbox."""

    def _last_code():
        return mail.outbox[-1].body.rsplit(': ', 1)[-1].strip()

    return _last_code


@pytest.fixture
def register(post):
    """Регистрирует пользователя через djoser."""

    def _register(email='alice@example.com', name='Alice', password=PWD):
        payload = {'email': email, 'name': name}
        if password is not None:
            payload['password'] = password
        return post(REGISTER, payload)

    return _register


@pytest.fixture
def register_and_code(register, last_code):
    """Регистрирует пользователя и сразу возвращает код из письма."""

    def _register_and_code(**kwargs):
        resp = register(**kwargs)
        return resp, last_code()

    return _register_and_code


@pytest.fixture
def active_user(db):
    """Создаёт уже активного пользователя, минуя флоу регистрации."""

    def _active_user(email='carol@example.com', password=PWD):
        user = User(email=email, name=email.split('@')[0], is_active=True)
        user.set_password(password)
        user.save()
        return user

    return _active_user


@pytest.fixture
def auth(api_client, post):
    """Логинит пользователя и прописывает access-токен в клиент."""

    def _auth(email, password):
        tok = post(TOKEN, {'email': email, 'password': password})
        api_client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {tok.data["access"]}'
        )
        return tok

    return _auth


@pytest.fixture
def make_offline_exercise(db):
    """Создаёт задание типа offline (для тестов прогресса профиля)."""

    def _make(title, is_active=True):
        return Exercise.objects.create(
            title=title,
            description='Описание',
            type='offline',
            difficulty='easy',
            question='Вопрос',
            is_active=is_active,
        )

    return _make


@pytest.fixture
def make_session():
    """Создаёт завершённую сессию прохождения задания."""

    def _make(user, exercise, success=True):
        started_at = timezone.now()
        return ExerciseSession.objects.create(
            user=user,
            exercise=exercise,
            difficulty=exercise.difficulty,
            started_at=started_at,
            finished_at=started_at + timedelta(minutes=1),
            duration_seconds=60,
            success=success,
            score=100 if success else 0,
        )

    return _make