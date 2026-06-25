"""drf-spectacular helpers for branch API documentation."""

from shared.openapi import document_api_view, document_crud_view, envelope_responses

PUBLIC_BRANCH_TAG = "Branch - Public"
TENANT_BRANCH_TAG = "Branch - Tenant"

__all__ = [
    "PUBLIC_BRANCH_TAG",
    "TENANT_BRANCH_TAG",
    "document_api_view",
    "document_crud_view",
    "envelope_responses",
]
