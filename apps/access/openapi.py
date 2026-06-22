"""drf-spectacular helpers for access API documentation."""

from shared.openapi import document_api_view, document_crud_view, envelope_responses

TENANT_ACCESS_TAG = "Access - Tenant"

__all__ = [
    "TENANT_ACCESS_TAG",
    "document_api_view",
    "document_crud_view",
    "envelope_responses",
]
