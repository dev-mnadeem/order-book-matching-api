"""Django settings for the TradeCore posts API.

Every value that differs between a laptop, CI and production is read from the
environment.  The defaults are chosen so that ``python manage.py runserver``
works on a fresh clone with no ``.env`` file at all: SQLite for storage and the
offline enrichment providers, so sign-up never depends on a third-party key.
"""

from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

from tradecore.env import env_bool, env_int, env_list, env_str

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

# --------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------

# Only the insecure development fallback is hard-coded.  Any deployment with
# DJANGO_DEBUG=false must supply a real DJANGO_SECRET_KEY (enforced below).
DEV_SECRET_KEY = "django-insecure-dev-only-do-not-use-in-production"

SECRET_KEY = env_str("DJANGO_SECRET_KEY", DEV_SECRET_KEY)
DEBUG = env_bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "[::1]"])
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

if not DEBUG and SECRET_KEY == DEV_SECRET_KEY:
    raise RuntimeError(
        "DJANGO_SECRET_KEY must be set to a unique value when DJANGO_DEBUG is false."
    )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "tradecore_api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tradecore.urls"
WSGI_APPLICATION = "tradecore.wsgi.application"
ASGI_APPLICATION = "tradecore.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------

DATABASES = {
    "default": dj_database_url.config(
        env="DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=env_int("DATABASE_CONN_MAX_AGE", 600),
        conn_health_checks=True,
    )
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "tradecore_api.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------------
# REST framework / auth
# --------------------------------------------------------------------------

# Page size for the post feed.  Without this the list endpoint returns every
# post a user has ever written in a single unbounded response.
POST_PAGE_SIZE = env_int("POST_PAGE_SIZE", 20)
POST_MAX_PAGE_SIZE = env_int("POST_MAX_PAGE_SIZE", 100)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # Deny by default.  Endpoints that are genuinely public opt out with an
    # explicit permission_classes = [AllowAny].
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "tradecore_api.pagination.PostPagination",
    "PAGE_SIZE": POST_PAGE_SIZE,
    "EXCEPTION_HANDLER": "tradecore_api.exceptions.api_exception_handler",
}

ACCESS_TOKEN_LIFETIME_MINUTES = env_int("ACCESS_TOKEN_LIFETIME_MINUTES", 60)
REFRESH_TOKEN_LIFETIME_DAYS = env_int("REFRESH_TOKEN_LIFETIME_DAYS", 1)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=ACCESS_TOKEN_LIFETIME_MINUTES),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=REFRESH_TOKEN_LIFETIME_DAYS),
    # "JWT" keeps the header format this API has always documented working
    # ("Authorization: JWT <token>"); "Bearer" is accepted for standard clients.
    "AUTH_HEADER_TYPES": ("JWT", "Bearer"),
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
}

# --------------------------------------------------------------------------
# Enrichment and moderation providers
# --------------------------------------------------------------------------

GEOLOCATION_PROVIDER = env_str("GEOLOCATION_PROVIDER", "auto")
HOLIDAY_PROVIDER = env_str("HOLIDAY_PROVIDER", "auto")
MODERATION_PROVIDER = env_str("MODERATION_PROVIDER", "auto")

ABSTRACT_GEOLOCATION_API_KEY = env_str("ABSTRACT_GEOLOCATION_API_KEY", "")
ABSTRACT_HOLIDAYS_API_KEY = env_str("ABSTRACT_HOLIDAYS_API_KEY", "")
ANTHROPIC_API_KEY = env_str("ANTHROPIC_API_KEY", "")
MODERATION_MODEL = env_str("MODERATION_MODEL", "claude-sonnet-4-5")

PROVIDER_HTTP_TIMEOUT_SECONDS = env_int("PROVIDER_HTTP_TIMEOUT_SECONDS", 5)
PROVIDER_HTTP_MAX_RETRIES = env_int("PROVIDER_HTTP_MAX_RETRIES", 2)
# Sign-up used to make one paid geolocation call per request.  Addresses map to
# a location far more slowly than users sign up, so the result is cached.
GEOLOCATION_CACHE_SECONDS = env_int("GEOLOCATION_CACHE_SECONDS", 24 * 60 * 60)
HOLIDAY_CACHE_SECONDS = env_int("HOLIDAY_CACHE_SECONDS", 6 * 60 * 60)

CACHES = {
    "default": {
        "BACKEND": env_str("CACHE_BACKEND", "django.core.cache.backends.locmem.LocMemCache"),
        "LOCATION": env_str("CACHE_LOCATION", "tradecore-local"),
    }
}

# --------------------------------------------------------------------------
# I18N / static
# --------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# --------------------------------------------------------------------------
# Security headers (active only when DEBUG is off)
# --------------------------------------------------------------------------

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env_int("DJANGO_SECURE_HSTS_SECONDS", 60 * 60 * 24 * 30)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "{levelname} {name} {message}", "style": "{"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": env_str("DJANGO_LOG_LEVEL", "INFO")},
}
