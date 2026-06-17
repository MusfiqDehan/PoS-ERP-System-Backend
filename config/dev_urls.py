"""Shared DEBUG-only URL patterns for local dev tooling."""

from django.conf import settings
from django.urls import include, path


def dev_tooling_urlpatterns():
    if not settings.DEBUG:
        return []
    return [
        path("__debug__/", include("debug_toolbar.urls")),
        path("silk/", include("silk.urls", namespace="silk")),
    ]
