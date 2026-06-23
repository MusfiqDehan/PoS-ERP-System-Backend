"""Shared Django settings for Sortorium Backend."""

from __future__ import annotations

import os
import socket
from datetime import timedelta
from pathlib import Path

import dj_database_url
from corsheaders.defaults import default_headers as cors_default_headers

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def is_running_in_docker() -> bool:
    return Path("/.dockerenv").exists()


def first_resolvable_host(host_candidates: list[str | None]) -> str | None:
    for host in host_candidates:
        if not host:
            continue
        try:
            socket.getaddrinfo(host, None)
            return host
        except OSError:
            continue
    return None


SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-s5gp6lsw-mzturp2^ku5$th^q#f0-^dk7za2a#u^)a)62y@8=j",
)

DEBUG = os.environ.get("DEBUG", "false").lower() in ("true", "1")

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("ALLOWED_HOSTS", "*").split(",") if h.strip()
]

SHARED_APPS = [
    "django_tenants",
    "apps.tenancy.apps.TenancyConfig",
    "apps.billing.apps.BillingConfig",
    "shared.apps.SharedConfig",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
]

TENANT_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "shared.apps.SharedConfig",
    "apps.tenancy.apps.TenancyConfig",
    "apps.access.apps.AccessConfig",
    "apps.branch.apps.BranchConfig",
    "apps.billing.apps.BillingConfig",
]

INSTALLED_APPS = list(SHARED_APPS) + [
    app for app in TENANT_APPS if app not in SHARED_APPS
]

TENANT_MODEL = "tenancy.Tenant"
TENANT_DOMAIN_MODEL = "tenancy.Domain"
PUBLIC_SCHEMA_URLCONF = "config.public_urls"
DATABASE_ROUTERS = ["django_tenants.routers.TenantSyncRouter"]
SHOW_PUBLIC_IF_NO_TENANT_FOUND = True

MIDDLEWARE = [
    "apps.tenancy.middleware.MobileAwareTenantMainMiddleware",
    "shared.middleware.timezone.TimezoneMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

_cors_allow_all = os.environ.get("CORS_ALLOW_ALL_ORIGINS", "true").lower() in (
    "true",
    "1",
)
CORS_ALLOW_ALL_ORIGINS = _cors_allow_all
if not _cors_allow_all:
    CORS_ALLOWED_ORIGINS = [
        o.strip()
        for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
        if o.strip()
    ]
    if DEBUG and not CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS = [
            "http://localhost:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
        ]

CORS_ALLOW_CREDENTIALS = os.environ.get("CORS_ALLOW_CREDENTIALS", "true").lower() in (
    "true",
    "1",
)
CORS_ALLOW_HEADERS = list(cors_default_headers) + [
    "x-tenant-subdomain",
    "x-tenant-schema",
]

_cors_allowed_origin_regexes = [
    o.strip()
    for o in os.environ.get("CORS_ALLOWED_ORIGIN_REGEXES", "").split(",")
    if o.strip()
]
if _cors_allowed_origin_regexes:
    CORS_ALLOWED_ORIGIN_REGEXES = _cors_allowed_origin_regexes
elif not DEBUG:
    root_domain = (
        os.environ.get("TENANT_ROOT_DOMAIN", "sortorium.com")
        .strip()
        .replace(".", r"\.")
    )
    CORS_ALLOWED_ORIGIN_REGEXES = [
        rf"^https://([a-z0-9-]+\.)?{root_domain}$",
    ]

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "false").lower() in (
    "true",
    "1",
)

PUBLIC_DOMAIN = os.environ.get("PUBLIC_DOMAIN", "").strip().lower()
TENANT_BASE_DOMAIN = os.environ.get("TENANT_BASE_DOMAIN", "").strip().lower()
TENANT_POST_LOGIN_PATH = (
    os.environ.get("TENANT_POST_LOGIN_PATH", "/dashboard").strip() or "/dashboard"
)
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "").strip()
PUBLIC_FRONTEND_URL = os.environ.get("PUBLIC_FRONTEND_URL", FRONTEND_BASE_URL).strip()
TENANT_FRONTEND_BASE_DOMAIN = (
    os.environ.get("TENANT_FRONTEND_BASE_DOMAIN", TENANT_BASE_DOMAIN).strip().lower()
)
TENANT_FRONTEND_SCHEME = os.environ.get(
    "TENANT_FRONTEND_SCHEME", "http" if DEBUG else "https"
).strip().lower() or ("http" if DEBUG else "https")
TENANT_FRONTEND_PORT = os.environ.get("TENANT_FRONTEND_PORT", "").strip()
TENANT_ONBOARDING_LINKS_PUBLIC = os.environ.get(
    "TENANT_ONBOARDING_LINKS_PUBLIC", "false"
).lower() in (
    "true",
    "1",
)
BACKEND_BASE_URL = (
    os.environ.get("BACKEND_BASE_URL", "http://localhost:8002").strip().rstrip("/")
)

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

try:
    DB_CONN_MAX_AGE = max(0, int(os.environ.get("DB_CONN_MAX_AGE", "0")))
except ValueError:
    DB_CONN_MAX_AGE = 0

if os.environ.get("USE_PGBOUNCER", "").strip().lower() in ("1", "true", "yes", "on"):
    DB_CONN_MAX_AGE = 0

_database_url = os.environ.get("DATABASE_URL", "")
if _database_url:
    _db_cfg = dj_database_url.parse(
        _database_url,
        conn_max_age=DB_CONN_MAX_AGE,
        conn_health_checks=not os.environ.get("USE_PGBOUNCER", "").strip().lower()
        in ("1", "true", "yes", "on"),
    )
    db_host = _db_cfg.get("HOST")
    if not is_running_in_docker() and db_host in {
        "db",
        "postgres",
        "postgresql",
        "sortorium-db-local",
    }:
        _db_cfg["HOST"] = os.environ.get("LOCAL_DB_HOST", "localhost")
        if not os.environ.get("LOCAL_DB_PORT") and str(_db_cfg.get("PORT") or "") in {
            "",
            "5432",
        }:
            _db_cfg["PORT"] = "5452"
        else:
            _db_cfg["PORT"] = (
                os.environ.get("LOCAL_DB_PORT") or _db_cfg.get("PORT") or 5432
            )
    if is_running_in_docker():
        resolved_host = first_resolvable_host(
            [
                _db_cfg.get("HOST"),
                os.environ.get("DOCKER_DB_HOST", ""),
                os.environ.get("POSTGRES_HOST", ""),
                "sortorium-db-local",
                "db",
                "postgres",
            ]
        )
        if resolved_host:
            _db_cfg["HOST"] = resolved_host
    _db_cfg["ENGINE"] = "django_tenants.postgresql_backend"
    if os.environ.get("USE_PGBOUNCER", "").strip().lower() in ("1", "true", "yes", "on"):
        # Required for PgBouncer transaction pooling with Django.
        _db_cfg["DISABLE_SERVER_SIDE_CURSORS"] = True
    DATABASES = {"default": _db_cfg}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django_tenants.postgresql_backend",
            "NAME": os.environ.get("DB_NAME", "sortorium_db"),
            "USER": os.environ.get("DB_USER", "postgres"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "CONN_MAX_AGE": DB_CONN_MAX_AGE,
            "CONN_HEALTH_CHECKS": True,
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = int(os.environ.get("CELERY_TASK_TIME_LIMIT", "300"))
CELERY_TASK_SOFT_TIME_LIMIT = int(os.environ.get("CELERY_TASK_SOFT_TIME_LIMIT", "240"))
CELERY_BEAT_SCHEDULE = {
    "process-email-queue": {
        "task": "apps.tenancy.tasks.process_email_queue_task",
        "schedule": timedelta(seconds=60),
    },
}

_redis_cache_url = os.environ.get("REDIS_CACHE_URL", "").strip()
if _redis_cache_url:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": _redis_cache_url,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            "KEY_PREFIX": "sortorium",
        }
    }
elif DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sortorium-dev-cache",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": "redis://redis:6379/2",
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            "KEY_PREFIX": "sortorium",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "tenancy.User"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "tenant_registration": "10/hour",
        "tenant_auth": "30/minute",
        "tenant_password_reset": "10/hour",
        "tenant_password_setup": "20/hour",
        "superadmin_invitation": "60/hour",
    },
    "EXCEPTION_HANDLER": "shared.responses.handler.custom_exception_handler",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "shared.pagination.CursorPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Sortorium PoS API",
    "DESCRIPTION": "API documentation for the Sortorium Point of Sale SaaS platform",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "SERVE_URLCONF": ["config.public_urls", "config.urls"],
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "SECURITY": [{"bearerAuth": []}],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
    "TAGS": [
        {
            "name": "Tenancy - Public",
            "description": "Unauthenticated public-schema tenant onboarding, auth, and password flows.",
        },
        {
            "name": "Tenancy - Tenant",
            "description": "Authenticated tenant-scoped user, branding, and settings operations.",
        },
        {
            "name": "Tenancy - Platform Admin",
            "description": "Platform administrator operations for tenant lifecycle and feature overrides.",
        },
        {
            "name": "Billing - Public",
            "description": "Unauthenticated payment gateway callbacks and subscription redirect handlers.",
        },
        {
            "name": "Billing - Tenant",
            "description": "Tenant administrator subscription, invoice, and gateway configuration operations.",
        },
        {
            "name": "Billing - Platform Admin",
            "description": "Platform administrator billing catalog, gateways, packages, and invoice management.",
        },
        {
            "name": "Access - Tenant",
            "description": "Tenant-scoped role-based access control for roles, permissions, and assignments.",
        },
        {
            "name": "Branch - Public",
            "description": "Unauthenticated read-only branch listings for tenant storefronts.",
        },
        {
            "name": "Branch - Tenant",
            "description": "Authenticated tenant branch management, summaries, and manager assignment.",
        },
    ],
    "POSTPROCESSING_HOOKS": [
        "config.openapi.enforce_operation_descriptions",
    ],
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
        "displayOperationId": False,
        "docExpansion": "list",
        "filter": True,
    },
}

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "False") == "True"
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "False") == "True"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", 15))
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", os.environ.get("EMAIL_HOST_USER", "noreply@example.com")
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
