"""Shared DEBUG-only URL patterns for local dev tooling."""

from django.apps import apps
from django.conf import settings
from django.urls import include, path


def dev_tooling_urlpatterns():
    if not settings.DEBUG:
        return []
    patterns = []
    if apps.is_installed("debug_toolbar"):
        patterns.append(path("__debug__/", include("debug_toolbar.urls")))
    if apps.is_installed("silk"):
        patterns.append(path("silk/", include("silk.urls", namespace="silk")))
    return patterns
