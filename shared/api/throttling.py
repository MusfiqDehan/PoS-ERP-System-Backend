"""
Custom DRF throttle classes.

Rate-limit responses are handled by the global exception handler
(``shared.responses.handler.custom_exception_handler``).
"""

from rest_framework import throttling

from shared.responses.handler import custom_exception_handler

# Backward-compatible alias — use custom_exception_handler in settings.
throttle_exception_handler = custom_exception_handler


class BurstAnonRateThrottle(throttling.AnonRateThrottle):
    """Short-window anonymous burst guard (default: 20/min)."""

    scope = "burst_anon"


class BurstUserRateThrottle(throttling.UserRateThrottle):
    """Short-window authenticated burst guard (default: 60/min)."""

    scope = "burst_user"


class SustainedAnonRateThrottle(throttling.AnonRateThrottle):
    """Long-window anonymous sustained guard (default: 500/hour)."""

    scope = "sustained_anon"


class SustainedUserRateThrottle(throttling.UserRateThrottle):
    """Long-window authenticated sustained guard (default: 2000/hour)."""

    scope = "sustained_user"
