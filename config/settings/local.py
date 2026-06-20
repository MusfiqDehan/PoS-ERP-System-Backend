"""Local development settings."""

from .base import *  # noqa: F403

DEBUG = True

EMAIL_BACKEND = os.environ.get(  # noqa: F405
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)

SHARED_APPS = list(SHARED_APPS) + [  # noqa: F405
    "debug_toolbar",
    "silk",
]
INSTALLED_APPS = list(SHARED_APPS) + [
    app for app in TENANT_APPS if app not in SHARED_APPS  # noqa: F405
]
INSTALLED_APPS += ["shared.testapp.apps.SharedTestappConfig"]
TENANT_APPS = list(TENANT_APPS) + ["shared.testapp.apps.SharedTestappConfig"]  # noqa: F405

MIDDLEWARE = [
    "apps.tenancy.middleware.MobileAwareTenantMainMiddleware",
    "shared.middleware.timezone.TimezoneMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "silk.middleware.SilkyMiddleware",
    *[
        middleware
        for middleware in MIDDLEWARE  # noqa: F405
        if middleware
        not in {
            "apps.tenancy.middleware.MobileAwareTenantMainMiddleware",
            "shared.middleware.timezone.TimezoneMiddleware",
        }
    ],
]

INTERNAL_IPS = ["127.0.0.1", "localhost"]
if is_running_in_docker():  # noqa: F405
    INTERNAL_IPS += [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
    ]

DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,  # noqa: F405
    # Silk uses cProfile when SILKY_PYTHON_PROFILER is enabled; Python allows
    # only one active profiler, so disable the duplicate debug-toolbar panel.
    "DISABLE_PANELS": [
        "debug_toolbar.panels.profiling.ProfilingPanel",
    ],
}

SILKY_PYTHON_PROFILER = True
SILKY_AUTHENTICATION = False
SILKY_AUTHORISATION = False
SILKY_META = True
