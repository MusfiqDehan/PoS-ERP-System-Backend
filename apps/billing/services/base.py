"""Abstract base class for payment gateway services."""

from abc import ABC, abstractmethod
from typing import Any


class AbstractPaymentGateway(ABC):
    @abstractmethod
    def initiate(self, transaction) -> dict[str, Any]:
        """Return dict with ``gateway_url`` key."""

    @abstractmethod
    def validate(self, val_id: str) -> dict[str, Any]:
        """Validate a completed payment by gateway validation id."""


def build_callback_urls(
    request, path_prefix: str = "/api/v1/billing/subscription"
) -> dict[str, str]:
    from django.conf import settings

    backend_base = (getattr(settings, "BACKEND_BASE_URL", "") or "").rstrip(
        "/"
    ) or request.build_absolute_uri("/").rstrip("/")
    return {
        "success_url": f"{backend_base}{path_prefix}/success/",
        "fail_url": f"{backend_base}{path_prefix}/fail/",
        "cancel_url": f"{backend_base}{path_prefix}/cancel/",
        "ipn_url": f"{backend_base}{path_prefix}/ipn/",
    }
