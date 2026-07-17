import os
import sys
from pathlib import Path
from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

def _env_bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


# Defaults to False so that FORGETTING to set DEBUG in a deployment fails safe (no
# tracebacks, no settings leak) instead of failing open. Local dev sets DEBUG=True
# explicitly in .env / docker-compose.
DEBUG = _env_bool('DEBUG', False)

_DEV_SECRET_KEY = 'django-insecure-paperdeck-dev-key-change-in-production'
SECRET_KEY = os.environ.get('SECRET_KEY', _DEV_SECRET_KEY)

# Refuse to serve production traffic with the shipped dev key. Django only *warns* about
# this, and a warning in a deploy log is exactly the kind of thing that gets missed —
# but this key signs every JWT and session cookie, so a leaked default is a full
# authentication bypass. Fail loudly at import instead.
if not DEBUG:
    if SECRET_KEY == _DEV_SECRET_KEY:
        raise ImproperlyConfigured(
            "SECRET_KEY is unset, so the insecure development key would be used. "
            "Set a real SECRET_KEY (50+ random characters) in the environment. "
            "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
        )
    if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5:
        raise ImproperlyConfigured(
            "SECRET_KEY is too weak (needs 50+ characters and 5+ distinct characters)."
        )

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost,api.paperdeck.databus.co,paperdeck.databus.co').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Provides SearchVector/SearchQuery, used to retrieve previous-year questions as
    # generation exemplars by MEANING rather than by an exact topic-string match
    # (papers/service/aigeneratorservice.py::_retrieve_exemplars). Postgres-only — the
    # project already cannot run on SQLite (courses/migrations/0003 is raw Postgres DDL).
    'django.contrib.postgres',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'storages',
    'users',
    'courses',
    'subjects',
    'staff',
    'students',
    'papers',
    'questions',
    'mocktests',
    'blueprints',
    'exams',
    'diagrams',
    'latex',
    'printtemplates',
    'billing',
    'attempts',
    'omr',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'paperdeck.urls'

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

WSGI_APPLICATION = 'paperdeck.wsgi.application'

if os.environ.get('USE_POSTGRES', 'False') == 'True':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'paperdeck'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            # 'OPTIONS': {'sslmode': 'require'},
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
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── Media storage ────────────────────────────────────────────────────────────────
# Media (rendered diagrams + user uploads: logos, thumbnails, syllabus files, OMR sheets)
# goes to Azure Blob Storage when credentials are configured, and falls back to the local
# filesystem otherwise so development works without Azure. Model FileField/ImageField pick
# this up automatically; the diagram engine writes through Django storage too (see
# diagrams/service/dispatcher.py).
AZURE_ACCOUNT_NAME = os.environ.get('AZURE_ACCOUNT_NAME', '')
AZURE_ACCOUNT_KEY = os.environ.get('AZURE_ACCOUNT_KEY', '')
AZURE_CONTAINER = os.environ.get('AZURE_CONTAINER', 'media')
# Never let the test suite write to real blob storage (slow, networked, pollutes the
# container) even when Azure credentials are present in the environment.
_RUNNING_TESTS = 'test' in sys.argv
_USE_AZURE_MEDIA = bool(AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY) and not _RUNNING_TESTS

if _USE_AZURE_MEDIA:
    # The container is PRIVATE: `.url()` returns a short-lived SAS-signed URL, so nothing in
    # blob storage is readable by a guessable public URL — exam content stays access-gated.
    # A model FileField regenerates its signed URL on every serialization, so expiry only
    # bounds how long a copied link stays live, not whether the UI can display the file.
    AZURE_URL_EXPIRATION_SECS = int(os.environ.get('AZURE_URL_EXPIRATION_SECS', 60 * 60 * 24))
    AZURE_OVERWRITE_FILES = False
    _default_storage_backend = 'storages.backends.azure_storage.AzureStorage'
else:
    _default_storage_backend = 'django.core.files.storage.FileSystemStorage'

STORAGES = {
    'default': {'BACKEND': _default_storage_backend},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'users.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(os.environ.get('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', 60))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.environ.get('JWT_REFRESH_TOKEN_LIFETIME_DAYS', 7))),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

from corsheaders.defaults import default_headers

CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']
CORS_ALLOW_HEADERS = list(default_headers) + ['Authorization', 'content-type', 'x-csrftoken']
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:5173,http://127.0.0.1:5173,http://localhost:5001'
).split(',')

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')


# ── Transport security (production only) ──────────────────────────────────────
# All of this is gated on `not DEBUG`: forcing HTTPS and secure-only cookies on a local
# HTTP dev server would just break login and hide the cookies from the browser.

# THE LOAD-BEARING LINE. Azure App Service (like most PaaS front ends) terminates TLS at
# the edge and forwards plain HTTP to the container, so `request.is_secure()` is False
# for every request no matter how the browser connected. Without this header mapping,
# SECURE_SSL_REDIRECT below would redirect every already-HTTPS request back to
# HTTPS — forever. The result is an infinite redirect loop, not a security failure, so
# it fails visibly rather than silently; but it takes the whole site down.
#
# This is only safe because the app sits BEHIND a proxy that always sets (and, crucially,
# overwrites) X-Forwarded-Proto. If it were ever exposed directly to the internet, a
# client could simply send the header itself and defeat the redirect. Azure's front end
# overwrites it, so a client cannot spoof it.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_SSL_REDIRECT = _env_bool('SECURE_SSL_REDIRECT', not DEBUG)

# The platform health probe may hit the container directly over HTTP, with no
# X-Forwarded-Proto — which would earn it a 301 and could be read as unhealthy. Exempt
# it. (Matched as a regex against the path with no leading slash.)
SECURE_REDIRECT_EXEMPT = [r'^api/health/?$']

# HSTS: tells browsers to refuse plain HTTP to this host for this long. Read the warning
# in Django's docs — it is effectively irreversible for the duration, because browsers
# cache it and you cannot recall it. It is correct here (the API is HTTPS-only), but if
# you are rolling it out for the first time, set SECURE_HSTS_SECONDS=3600 for a day,
# confirm nothing breaks, then raise it.
# `preload` is left OFF on purpose: submitting to the browser preload list is the one
# step that genuinely cannot be undone quickly.
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', 0 if DEBUG else 31536000))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', not DEBUG)
SECURE_HSTS_PRELOAD = _env_bool('SECURE_HSTS_PRELOAD', False)

# Django's W021 wants SECURE_HSTS_PRELOAD=True. We deliberately don't set it, and this
# silences the check rather than pretending otherwise.
#
# The `preload` directive is a declaration of intent to be added to the browsers' built-in
# HSTS preload list, and it does nothing on its own — you must submit the domain at
# hstspreload.org. That list keys on the *registrable* domain (databus.co), not on
# api.paperdeck.databus.co, so preloading this API alone is not even possible; submitting
# databus.co would force HTTPS on every sibling subdomain and is slow to reverse.
# That is an apex-domain decision, not an API one. Set SECURE_HSTS_PRELOAD=True to opt in
# (which also un-silences the check).
SILENCED_SYSTEM_CHECKS = [] if SECURE_HSTS_PRELOAD else ['security.W021']

# Never let the session or CSRF cookie travel over plain HTTP.
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# Django 4+ checks the Origin header against this for unsafe methods. Behind a TLS-
# terminating proxy the origin is https://…, which will not match a bare host, so the
# Django admin login would fail CSRF validation without it. Derived from ALLOWED_HOSTS.
CSRF_TRUSTED_ORIGINS = [
    f'https://{h.strip()}' for h in ALLOWED_HOSTS
    if h.strip() and h.strip() not in ('*', 'localhost', '127.0.0.1')
]
