"""
Master Configuration File for the SIPORA Backend.

This module houses all deployment environments, installed applications, middleware stacks,
database connectors, security policies (CORS/CSRF), and third-party integrations (SimpleJWT, SMTP).
"""

from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# Dynamically load the contiguous .env file natively if not operating within the Railway production container.
if not os.getenv('RAILWAY_STATIC_URL'):
    load_dotenv(os.path.join(BASE_DIR, '.env'), override=False)

SECRET_KEY = os.getenv('SECRET_KEY')

PRODUCTION = os.getenv('PRODUCTION', 'False').strip('\"\'').lower() == 'true'
DEBUG = os.getenv('DEBUG', 'True').strip('\"\'').lower() == 'true'

ALLOWED_HOST_ENV = os.getenv('ALLOWED_HOSTS')
if ALLOWED_HOST_ENV:
    ALLOWED_HOSTS = ALLOWED_HOST_ENV.split(',')
else:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1", "*"] 

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'core',
    'akun',
    'log_aktivitas',
    'laporan_kerusakan',
    'tanggapan',
    'aspirasi',
    'laporan_bullying',
    'artikel',
]

AUTH_USER_MODEL = 'akun.Pengguna'

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'core.middleware.TimingMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'sipora_be.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'sipora_be.wsgi.application'

if PRODUCTION:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER'),
            'PASSWORD': os.getenv('DB_PASSWORD'),
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT'),
            'OPTIONS': {
                'sslmode': 'require',
            },
            'CONN_MAX_AGE': 600,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
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

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Jakarta'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── Static files & Media Storage ─────────────────────────────────────────────
if PRODUCTION:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Cross-Origin Resource Sharing (CORS) & CSRF ──────────────────────────────
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://sipora-fe.vercel.app').strip('\"\'')
FRONTEND_ORIGIN = FRONTEND_URL.rstrip('/')

CORS_ALLOWED_ORIGINS = [
    FRONTEND_ORIGIN,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://sipora-fe.vercel.app",
]

CSRF_TRUSTED_ORIGINS = [
    FRONTEND_ORIGIN,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://sipora-fe.vercel.app",
]

CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'core.authentication.CookieJWTAuthentication',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'core.renderers.CoreJSONRenderer',
    ],
    'EXCEPTION_HANDLER': 'core.exceptions.core_exception_handler',
}

AUTH_COOKIE = 'access_token'
AUTH_COOKIE_REFRESH = 'refresh_token'
AUTH_COOKIE_SECURE = PRODUCTION
AUTH_COOKIE_HTTP_ONLY = True
AUTH_COOKIE_PATH = '/'
AUTH_COOKIE_SAMESITE = 'None' if PRODUCTION else 'Lax'

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ─── Email Configuration ──────────────────────────────────────────────────────
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '10'))
EMAIL_USE_CONSOLE_BACKEND = os.getenv('EMAIL_USE_CONSOLE_BACKEND', 'False').lower() == 'true'
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', f'SIPORA SMP Desa Putera <{EMAIL_HOST_USER}>')

if EMAIL_USE_CONSOLE_BACKEND:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Cryptographic TTL length for SMTP password resets.
PASSWORD_RESET_TIMEOUT = 3600

# ─── Railway / Containerized IPv4 Resolution Fix ──────────────────────────────
if PRODUCTION:
    import socket
    import smtplib
    
    # Store reference to the original C-level socket resolution method.
    orig_getaddrinfo = socket.getaddrinfo

    def forced_ipv4_getaddrinfo(*args, **kwargs):
        if len(args) > 0 and 'googlemail' in str(args[0]) or 'gmail' in str(args[0]):
            return orig_getaddrinfo(args[0], args[1], socket.AF_INET, socket.SOCK_STREAM)
        return orig_getaddrinfo(*args, **kwargs)

    socket.getaddrinfo = forced_ipv4_getaddrinfo