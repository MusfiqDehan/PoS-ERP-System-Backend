from __future__ import annotations

from uuid import UUID

from django_tenants.utils import get_public_schema_name, schema_context

from apps.tenancy.models import Tenant
from apps.tenancy.services.features import patch_tenant_feature_overrides


class TenantAdministrationService:
    @staticmethod
    def list_tenants_queryset():
        with schema_context(get_public_schema_name()):
            tenant_ids = list(
                Tenant.objects.order_by("name").values_list("id", flat=True)
            )
        return (
            Tenant.objects.filter(id__in=tenant_ids)
            .prefetch_related("domains")
            .order_by("name")
        )

    @staticmethod
    def get_tenant_feature_overrides(tenant_id: UUID) -> dict | None:
        tenant = Tenant.objects.filter(pk=tenant_id).first()
        if tenant is None:
            return None
        return tenant.features or {}

    @staticmethod
    def patch_tenant_feature_overrides_for_admin(
        tenant_id: UUID,
        overrides: dict,
    ) -> dict | None:
        tenant = Tenant.objects.filter(pk=tenant_id).first()
        if tenant is None:
            return None
        return patch_tenant_feature_overrides(tenant, overrides)
