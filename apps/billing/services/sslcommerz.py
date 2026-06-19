"""SSLCommerz payment gateway implementation."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from django.conf import settings

from apps.billing.services.base import AbstractPaymentGateway

logger = logging.getLogger(__name__)

SANDBOX_BASE = "https://sandbox.sslcommerz.com"
LIVE_BASE = "https://securepay.sslcommerz.com"
SESSION_API = "gwprocess/v4/api.php"
VALIDATE_API = "validator/api/validationserverAPI.php"


class SSLCommerzService(AbstractPaymentGateway):
    def __init__(
        self,
        store_id: str,
        store_password: str,
        is_sandbox: bool,
        *,
        success_url: str,
        fail_url: str,
        cancel_url: str,
        ipn_url: str,
    ):
        self.store_id = store_id
        self.store_password = store_password
        self.is_sandbox = is_sandbox
        self._base = SANDBOX_BASE if is_sandbox else LIVE_BASE
        self.success_url = success_url
        self.fail_url = fail_url
        self.cancel_url = cancel_url
        self.ipn_url = ipn_url

    def _post_form(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        encoded = urllib.parse.urlencode(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=encoded,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            logger.error("SSLCommerz POST failed: %s", exc)
            raise ValueError(f"SSLCommerz session init failed: {exc}") from exc
        return json.loads(body)

    def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        query = urllib.parse.urlencode(params)
        full_url = f"{url}?{query}"
        try:
            with urllib.request.urlopen(full_url, timeout=30) as response:
                body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            logger.error("SSLCommerz GET failed: %s", exc)
            raise ValueError(f"SSLCommerz validation failed: {exc}") from exc
        return json.loads(body)

    def initiate(self, transaction) -> dict[str, Any]:
        tenant = getattr(transaction, "tenant", None)

        def _first(*values: Any) -> str:
            for value in values:
                text = str(value or "").strip()
                if text:
                    return text
            return ""

        default_phone = (
            getattr(settings, "SSLCOMMERZ_FALLBACK_PHONE", "01700000000")
            or "01700000000"
        ).strip()
        metadata = getattr(tenant, "metadata", {}) or {}

        payload = {
            "store_id": self.store_id,
            "store_passwd": self.store_password,
            "total_amount": str(transaction.amount),
            "currency": transaction.currency,
            "tran_id": transaction.tran_id,
            "success_url": self.success_url,
            "fail_url": self.fail_url,
            "cancel_url": self.cancel_url,
            "ipn_url": self.ipn_url,
            "cus_name": _first(
                getattr(transaction, "customer_name", ""),
                getattr(tenant, "name", ""),
                "Customer",
            ),
            "cus_email": _first(
                getattr(transaction, "customer_email", ""),
                getattr(tenant, "billing_email", ""),
                getattr(tenant, "owner_email", ""),
                "support@example.com",
            ),
            "cus_phone": _first(
                getattr(transaction, "customer_phone", ""),
                metadata.get("contact_phone", ""),
                default_phone,
            ),
            "cus_add1": "N/A",
            "cus_city": "Dhaka",
            "cus_country": "Bangladesh",
            "shipping_method": "NO",
            "product_name": "Sortorium Subscription",
            "product_category": "Service",
            "product_profile": "service",
        }

        data = self._post_form(f"{self._base}/{SESSION_API}", payload)
        if data.get("status") != "SUCCESS":
            raise ValueError(
                data.get("failedreason") or "SSLCommerz session init failed."
            )

        gateway_url = data.get("GatewayPageURL") or data.get("redirectGatewayURL")
        if not gateway_url:
            raise ValueError("SSLCommerz did not return a gateway URL.")
        return {"gateway_url": gateway_url, "raw": data}

    def validate(self, val_id: str) -> dict[str, Any]:
        return self._get_json(
            f"{self._base}/{VALIDATE_API}",
            {
                "val_id": val_id,
                "store_id": self.store_id,
                "store_passwd": self.store_password,
                "format": "json",
            },
        )
