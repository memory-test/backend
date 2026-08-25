from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from authentication.models import EmailCode

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
        payload = {'email': email, 'name': name}
        if password is not None:
            payload['password'] = password
        return self._post(REGISTER, payload)

    def _register_and_code(self, **kwargs):
        resp = self._register(**kwargs)
        return resp, last_code()

    def _active_user(self, email='carol@example.com', password=PWD):
        user = User(email=email, name=email.split('@')[0], is_active=True)
        user.set_password(password)
        user.save()
        return user

    def _auth(self, email, password):
        tok = self._post(TOKEN, {'email': email, 'password': password})
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {tok.data["access"]}'
        )
        return tok

    # --- регистрация (djoser) ------------------------------------------
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
        resp = self._register(password=None)
        self.assertEqual(resp.status_code, 201)
        self.assertFalse(
            User.objects.get(email='alice@example.com').has_usable_password()
        )

    def test_resend_activation_sends_new_code(self):
        self._register()
        mail.outbox = []
        # имитируем прошедший кулдаун, иначе повторная отправка молча
        # пропускается
        EmailCode.objects.update(
            created_at=timezone.now() - timedelta(minutes=2)
        )
        resp = self._post(RESEND_ACTIVATION, {'email': 'alice@example.com'})
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_activation_for_unknown_email_is_silent(self):
        resp = self._post(RESEND_ACTIVATION, {'email': 'noone@example.com'})
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(len(mail.outbox), 0)

    def test_resend_activation_cooldown_is_silent(self):
        """Кулдаун не роняет эндпоинт djoser — код просто не отправляется."""
        self._register()
        resp = self._post(RESEND_ACTIVATION, {'email': 'alice@example.com'})
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(len(mail.outbox), 1)

    # --- подтверждение кода -------------------------------------------
    def test_verify_registration_activates_and_returns_jwt(self):
        _, code = self._register_and_code()
        resp = self._post(
            VERIFY,
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
            VERIFY,
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
            VERIFY,
            {
                'email': 'alice@example.com',
                'code': code,
                'purpose': 'registration',
            },
        )
        self.assertEqual(first.status_code, 200)
        second = self._post(
            VERIFY,
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
            VERIFY,
            {
                'email': 'alice@example.com',
                'code': code,
                'purpose': 'registration',
            },
        )
        self.assertEqual(resp.status_code, 400)

    def test_code_login_returns_jwt(self):
        self._active_user(email='frank@example.com')
        self._post(CODE_REQUEST, {'email': 'frank@example.com'})
        code = last_code()
        resp = self._post(
            VERIFY,
            {
                'email': 'frank@example.com',
                'code': code,
                'purpose': 'login',
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)

    # --- вход по паролю (djoser jwt) -----------------------------------
    def test_token_login_by_password(self):
        self._active_user()
        resp = self._post(
            TOKEN, {'email': 'carol@example.com', 'password': PWD}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)

    def test_token_login_wrong_password(self):
        self._active_user()
        resp = self._post(
            TOKEN,
            {'email': 'carol@example.com', 'password': 'wrong'},
        )
        self.assertEqual(resp.status_code, 401)

    def test_token_refresh(self):
        self._active_user(email='gina@example.com')
        tok = self._post(TOKEN, {'email': 'gina@example.com', 'password': PWD})
        resp = self._post(REFRESH, {'refresh': tok.data['refresh']})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)

    # --- сброс пароля (djoser + код) -----------------------------------
    def test_password_reset_flow(self):
        self._active_user(email='dave@example.com')
        resp = self._post(RESET, {'email': 'dave@example.com'})
        self.assertEqual(resp.status_code, 204)
        code = last_code()
        new_pwd = 'BrandNew-Passw0rd-99'
        resp = self._post(
            RESET_CONFIRM,
            {
                'email': 'dave@example.com',
                'code': code,
                'new_password': new_pwd,
            },
        )
        self.assertEqual(resp.status_code, 204)
        resp = self._post(
            TOKEN, {'email': 'dave@example.com', 'password': new_pwd}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)

    def test_password_reset_unknown_email_is_generic(self):
        resp = self._post(RESET, {'email': 'noone@example.com'})
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_confirm_weak_password_keeps_code(self):
        """Слабый пароль не «сжигает» код: проверка идёт до расходования."""
        self._active_user(email='dave@example.com')
        self._post(RESET, {'email': 'dave@example.com'})
        code = last_code()
        resp = self._post(
            RESET_CONFIRM,
            {
                'email': 'dave@example.com',
                'code': code,
                'new_password': '123',
            },
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('new_password', resp.data)
        resp = self._post(
            RESET_CONFIRM,
            {
                'email': 'dave@example.com',
                'code': code,
                'new_password': 'BrandNew-Passw0rd-99',
            },
        )
        self.assertEqual(resp.status_code, 204)

    def test_password_reset_blacklists_old_tokens(self):
        self._active_user(email='dave@example.com')
        tok = self._post(TOKEN, {'email': 'dave@example.com', 'password': PWD})
        self._post(RESET, {'email': 'dave@example.com'})
        code = last_code()
        resp = self._post(
            RESET_CONFIRM,
            {
                'email': 'dave@example.com',
                'code': code,
                'new_password': 'BrandNew-Passw0rd-99',
            },
        )
        self.assertEqual(resp.status_code, 204)
        refreshed = self._post(REFRESH, {'refresh': tok.data['refresh']})
        self.assertEqual(refreshed.status_code, 401)

    # --- рейт-лимиты / анти-enumeration -------------------------------
    def test_code_request_cooldown(self):
        self._active_user(email='eve@example.com')
        first = self._post(CODE_REQUEST, {'email': 'eve@example.com'})
        self.assertEqual(first.status_code, 200)
        second = self._post(CODE_REQUEST, {'email': 'eve@example.com'})
        self.assertEqual(second.status_code, 429)

    # --- профиль текущего пользователя (djoser me) ---------------------
    def test_me_requires_auth(self):
        resp = self.client.get(f'{API}{ME}')
        self.assertEqual(resp.status_code, 401)

    def test_me_returns_profile(self):
        self._active_user()
        self._auth('carol@example.com', PWD)
        resp = self.client.get(f'{API}{ME}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['email'], 'carol@example.com')

    def test_me_role_is_read_only(self):
        self._active_user()
        self._auth('carol@example.com', PWD)
        resp = self.client.patch(
            f'{API}{ME}', {'role': 'admin'}, format='json'
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            User.objects.get(email='carol@example.com').role, 'user'
        )
