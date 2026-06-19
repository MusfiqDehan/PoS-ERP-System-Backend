from apps.billing.services.base import AbstractPaymentGateway
from apps.billing.services.sslcommerz import SSLCommerzService


def get_gateway(
    slug: str,
    credentials: dict,
    is_sandbox: bool,
    *,
    success_url: str,
    fail_url: str,
    cancel_url: str,
    ipn_url: str,
) -> AbstractPaymentGateway:
    if slug == "sslcommerz":
        return SSLCommerzService(
            store_id=credentials.get("store_id", ""),
            store_password=credentials.get("store_password", ""),
            is_sandbox=is_sandbox,
            success_url=success_url,
            fail_url=fail_url,
            cancel_url=cancel_url,
            ipn_url=ipn_url,
        )
    raise ValueError(f"Unknown payment gateway: '{slug}'")
