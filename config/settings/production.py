"""Production settings."""

import os

from .base import *  # noqa: F403

DEBUG = False
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "true").lower() in (
    "true",
    "1",
)
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
