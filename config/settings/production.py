"""Production settings."""

from .base import *  # noqa: F403

DEBUG = False
SECURE_SSL_REDIRECT = os.environ.get(
    "SECURE_SSL_REDIRECT", "true"
).lower() in (  # noqa: F405
    "true",
    "1",
)
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
