"""drf-spectacular helpers for billing API documentation."""

from shared.openapi import document_api_view, document_crud_view, envelope_responses

PUBLIC_BILLING_TAG = "Billing - Public"
PLATFORM_BILLING_TAG = "Billing - Platform Admin"
TENANT_BILLING_TAG = "Billing - Tenant"

__all__ = [
    "PUBLIC_BILLING_TAG",
    "PLATFORM_BILLING_TAG",
    "TENANT_BILLING_TAG",
    "document_api_view",
    "document_crud_view",
    "envelope_responses",
]
