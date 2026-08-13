from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from authentication.models import EmailCode

User = get_user_model()

API = '/api/v1'
LOCMEM = 'django.core.mail.backends.locmem.EmailBackend'
PWD = 'Str0ng-Passw0rd-2026'


def last_code():
    """Достаёт код из тела последнего письма в тестовом outbox."""
    return mail.outbox[-1].body.rsplit(': ', 1)[-1].strip()


@override_settings(EMAIL_BACKEND=LOCMEM)
class AuthTests(TestCase):
    """Покрытие флоу авторизации: регистрация, код, вход, сброс пароля."""

    def setUp(self):
        self.client = APIClient()
        mail.outbox = []

    # --- helpers -------------------------------------------------------
    def _post(self, path, data):
        return self.client.post(f'{API}{path}', data, format='json')

    def _register(self, email='alice@example.com', name='Alice', password=PWD):
        return self._post(
            '/auth/register/',
            {'email': email, 'name': name, 'password': password},
        )

    def _register_and_code(self, **kwargs):
        resp = self._register(**kwargs)
        return resp, last_code()

    def _active_user(self, email='carol@example.com', password=PWD):
        user = User(email=email, name=email.split('@')[0], is_active=True)
        user.set_password(password)
        user.save()
        return user

    # --- регистрация ---------------------------------------------------
    def test_register_creates_inactive_user_and_sends_code(self):
        resp = self._register()
        self.assertEqual(resp.status_code, 201)
        self.assertFalse(User.objects.get(email='alice@example.com').is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('alice@example.com', mail.outbox[0].to)

    def test_register_duplicate_email(self):
        self._register()
        resp = self._register()
        self.assertEqual(resp.status_code, 400)
        self.assertIn('email', resp.data)

    def test_register_weak_password(self):
        resp = self._register(password='123')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('password', resp.data)

    def test_register_without_password_is_simplified(self):
        resp = self._post(
            '/auth/register/',
            {'email': 'bob@example.com', 'name': 'Bob'},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertFalse(
            User.objects.get(email='bob@example.com').has_usable_password()
        )

    # --- подтверждение кода -------------------------------------------
    def test_verify_registration_activates_and_returns_jwt(self):
        _, code = self._register_and_code()
        resp = self._post(
            '/auth/verify/',
            {
                'email': 'alice@example.com',
                'code': code,
                'purpose': 'registration',
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)
        self.assertTrue(User.objects.get(email='alice@example.com').is_active)

    def test_verify_wrong_code(self):
        self._register()
        resp = self._post(
            '/auth/verify/',
            {
                'email': 'alice@example.com',
                'code': '000000',
                'purpose': 'registration',
            },
        )
        self.assertEqual(resp.status_code, 400)

    def test_verify_reuse_code_rejected(self):
        _, code = self._register_and_code()
        first = self._post(
            '/auth/verify/',
            {
                'email': 'alice@example.com',
                'code': code,
                'purpose': 'registration',
            },
        )
        self.assertEqual(first.status_code, 200)
        second = self._post(
            '/auth/verify/',
            {
                'email': 'alice@example.com',
                'code': code,
                'purpose': 'registration',
            },
        )
        self.assertEqual(second.status_code, 400)

    def test_verify_expired_code_rejected(self):
        _, code = self._register_and_code()
        code_obj = EmailCode.objects.filter(
            email='alice@example.com', purpose='registration'
        ).latest('created_at')
        code_obj.expires_at = timezone.now() - timedelta(minutes=1)
        code_obj.save()
        resp = self._post(
            '/auth/verify/',
            {
                'email': 'alice@example.com',
                'code': code,
                'purpose': 'registration',
            },
        )
        self.assertEqual(resp.status_code, 400)

    def test_code_login_returns_jwt(self):
        self._active_user(email='frank@example.com')
        self._post(
            '/auth/code/request/',
            {'email': 'frank@example.com', 'purpose': 'login'},
        )
        code = last_code()
        resp = self._post(
            '/auth/verify/',
            {
                'email': 'frank@example.com',
                'code': code,
                'purpose': 'login',
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)

    # --- вход по паролю -----------------------------------------------
    def test_token_login_by_password(self):
        self._active_user()
        resp = self._post(
            '/token/', {'email': 'carol@example.com', 'password': PWD}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)

    def test_token_login_wrong_password(self):
        self._active_user()
        resp = self._post(
            '/token/',
            {'email': 'carol@example.com', 'password': 'wrong'},
        )
        self.assertEqual(resp.status_code, 401)

    def test_token_refresh(self):
        self._active_user(email='gina@example.com')
        tok = self._post(
            '/token/', {'email': 'gina@example.com', 'password': PWD}
        )
        resp = self._post('/token/refresh/', {'refresh': tok.data['refresh']})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)

    # --- сброс пароля --------------------------------------------------
    def test_password_reset_flow(self):
        self._active_user(email='dave@example.com')
        resp = self._post(
            '/auth/password/reset/', {'email': 'dave@example.com'}
        )
        self.assertEqual(resp.status_code, 200)
        code = last_code()
        new_pwd = 'BrandNew-Passw0rd-99'
        resp = self._post(
            '/auth/password/reset/confirm/',
            {
                'email': 'dave@example.com',
                'code': code,
                'new_password': new_pwd,
            },
        )
        self.assertEqual(resp.status_code, 200)
        resp = self._post(
            '/token/', {'email': 'dave@example.com', 'password': new_pwd}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)

    def test_password_reset_unknown_email_is_generic(self):
        resp = self._post(
            '/auth/password/reset/', {'email': 'noone@example.com'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    # --- рейт-лимиты / анти-enumeration -------------------------------
    def test_code_request_cooldown(self):
        self._active_user(email='eve@example.com')
        first = self._post(
            '/auth/code/request/',
            {'email': 'eve@example.com', 'purpose': 'login'},
        )
        self.assertEqual(first.status_code, 200)
        second = self._post(
            '/auth/code/request/',
            {'email': 'eve@example.com', 'purpose': 'login'},
        )
        self.assertEqual(second.status_code, 429)

    # --- профиль текущего пользователя --------------------------------
    def test_me_requires_auth(self):
        resp = self.client.get(f'{API}/users/me/')
        self.assertEqual(resp.status_code, 401)

    def test_me_returns_profile(self):
        self._active_user()
        tok = self._post(
            '/token/', {'email': 'carol@example.com', 'password': PWD}
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {tok.data["access"]}'
        )
        resp = self.client.get(f'{API}/users/me/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['email'], 'carol@example.com')
