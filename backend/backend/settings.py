import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = os.getenv('SECRET_KEY', 'secrect')

DEBUG = os.getenv('DEBUG', 'True') in ['True', '1']

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(
    ','
)

CSRF_TRUSTED_ORIGINS = [f'https://{host}' for host in ALLOWED_HOSTS]
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://127.0.0.1:5173,http://localhost:5173').split(
    ','
)

AUTH_USER_MODEL = 'users.User'


INSTALLED_APPS = [
    # Django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Сторонние
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'django_filters',
    'djoser',
    'drf_spectacular',
    # Локальные приложения
    'authentication.apps.AuthenticationConfig',
    'users.apps.UsersConfig',
    'exercises.apps.ExercisesConfig',
    'progress.apps.ProgressConfig',
    'api.apps.ApiConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES_DIR = BASE_DIR / 'templates'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATES_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'django'),
        'USER': os.getenv('POSTGRES_USER', 'django'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'db'),
        'PORT': os.getenv('DB_PORT', 5432),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'ru-RU'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


STATIC_URL = '/static/'

STATIC_ROOT = Path('/var/www/django/static')

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

MEDIA_URL = '/media/'
MEDIA_ROOT = Path('/var/www/django/media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'api.pagination.PageNumberLimitPagination',
    'PAGE_SIZE': 5,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Memory Trainer API',
    'DESCRIPTION': 'API для тренажера памяти',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'ENUM_NAME_OVERRIDES': {
        'DifficultyEnum': 'users.models.Difficulty.choices',
    },
    'POSTPROCESSING_HOOKS': [
        'api.v1.schema.hooks.add_tags_by_path',
    ],
    'TAGS': [
        {
            'name': 'Авторизация',
            'description': 'Вход, токены, коды подтверждения',
        },
        {'name': 'Профиль', 'description': 'Управление профилем пользователя'},
        {'name': 'Задания', 'description': 'Задания и упражнения'},
        {'name': 'Прогресс', 'description': 'История и прогресс прохождения'},
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# djoser: регистрация/профиль/сброс пароля/JWT из коробки.
# Активация и сброс переопределены под 6-значные коды —
# см. authentication/djoser.py (код-движок authentication/services.py)
DJOSER = {
    'LOGIN_FIELD': 'email',
    'SEND_ACTIVATION_EMAIL': True,
    'HIDE_USERS': True,
    'SERIALIZERS': {
        'user': 'authentication.djoser.CodeUserSerializer',
        'current_user': 'authentication.djoser.CodeUserSerializer',
        'user_create': 'authentication.djoser.CodeUserCreateSerializer',
        'activation': 'authentication.djoser.CodeActivationSerializer',
        'password_reset_confirm': (
            'authentication.djoser.CodePasswordResetConfirmSerializer'
        ),
    },
    'EMAIL': {
        'activation': 'authentication.djoser.CodeActivationEmail',
        'password_reset': 'authentication.djoser.CodePasswordResetEmail',
    },
}

# Email: по умолчанию коды пишутся в консоль (локальная разработка),
# в проде бэкенд задаётся через окружение
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') in ['True', '1']
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False') in ['True', '1']
DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL', 'Тренажёр памяти <no-reply@example.com>'
)


SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            'format': '%(asctime)s %(levelname)s %(name)s: %(message)s [in %(pathname)s:%(lineno)d]',
        },
    },
    'handlers': {
        # Always active — writes to stdout, which is what `docker logs` reads
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'console',
            'level': 'DEBUG',
        },
    },
    # Catch-all for project apps and third-party libraries. Without it their
    # records reach a handler-less root logger and are dropped silently.
    'root': {
        'handlers': ['console'],
        'level': DEBUG,
    },
    'loggers': {
        # Django internals — pinned to INFO so LOG_LEVEL=DEBUG does not flood
        # the console with autoreload and template chatter
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # SQL queries — INFO to avoid flooding, switch to DEBUG when needed
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
