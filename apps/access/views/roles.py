"""API views for tenant-scoped RBAC."""

from django.db import connection, transaction
from django_tenants.utils import get_public_schema_name
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.access.models import Role, RolePermission, UserRole
from apps.access.permissions import IsRoleAdmin
from apps.access.serializers import (
    RolePermissionsBulkSerializer,
    RoleSerializer,
    UserRoleSerializer,
)
from apps.access.services.permissions import get_user_permission_map
from apps.tenancy.feature_registry import TENANT_REGISTRY
from apps.tenancy.services import get_tenant_enabled_feature_keys
from shared.cache.helpers import (
    ACCESS_ME_TTL,
    access_me_key,
    get_cached_value,
    invalidate_role_permissions,
    invalidate_user_permissions,
)
from shared.responses import error_response, list_success_response, success_response
from shared.responses.error_codes import ErrorCode
from shared.tenancy.helpers import is_tenant_admin_user, scope_queryset_by_branch_access
from shared.views import ModelCRUDView


class RoleListCreateView(ModelCRUDView):
    queryset = (
        Role.objects.all()
        .prefetch_related("permissions", "user_assignments")
        .order_by("name")
    )
    serializer_class = RoleSerializer
    permission_classes = [IsRoleAdmin]
    pagination_class = None

    def get_success_message(self, action: str) -> str:
        return {
            "list": "Roles retrieved successfully.",
            "create": "Role created successfully.",
        }.get(action, "Operation successful.")


class RoleDetailView(ModelCRUDView):
    queryset = Role.objects.all().prefetch_related("permissions")
    serializer_class = RoleSerializer
    permission_classes = [IsRoleAdmin]
    pagination_class = None

    def delete(self, request, pk, **kwargs):
        instance = self.get_object()
        if instance.is_system:
            return error_response(
                message="System roles cannot be deleted.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        role_id = instance.id
        instance.delete()
        invalidate_role_permissions(connection.schema_name, role_id)
        return success_response(
            data={}, message="Role deleted.", http_status=status.HTTP_200_OK
        )


class RolePermissionsView(APIView):
    permission_classes = [IsRoleAdmin]

    def get(self, request, role_id):
        role = generics.get_object_or_404(Role, pk=role_id)
        return success_response(
            data={
                "role_id": str(role.id),
                "permissions": list(
                    role.permissions.values("feature_key", "permission_level")
                ),
            },
            message="Role permissions retrieved.",
        )

    def put(self, request, role_id):
        role = generics.get_object_or_404(Role, pk=role_id)
        serializer = RolePermissionsBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            existing = {p.feature_key: p for p in role.permissions.all()}
            sent_keys = set()
            for entry in serializer.validated_data["permissions"]:
                key = entry["feature_key"]
                level = entry["permission_level"]
                sent_keys.add(key)
                if key in existing:
                    perm = existing[key]
                    if perm.permission_level != level:
                        perm.permission_level = level
                        perm.save(update_fields=["permission_level"])
                else:
                    RolePermission.objects.create(
                        role=role, feature_key=key, permission_level=level
                    )
            for key, perm in existing.items():
                if key not in sent_keys:
                    perm.delete()
        invalidate_role_permissions(connection.schema_name, role.id)
        return success_response(data={"status": "ok"}, message="Permissions updated.")


class UserRoleListCreateView(ModelCRUDView):
    queryset = UserRole.objects.select_related("role", "branch").all().order_by("id")
    serializer_class = UserRoleSerializer
    permission_classes = [IsRoleAdmin]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        return scope_queryset_by_branch_access(
            queryset,
            self.request.user,
            branch_field="branch_id",
            branch_filter_id=self.request.query_params.get("branch"),
        )

    def _create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_email = getattr(request.user, "email", "") or ""
        instance = serializer.save(assigned_by_email=actor_email)
        invalidate_user_permissions(connection.schema_name, instance.user_id)
        return success_response(
            data=self.get_serializer(instance).data,
            message=self.get_success_message("create"),
            http_status=status.HTTP_201_CREATED,
        )


class UserRoleDetailView(ModelCRUDView):
    queryset = UserRole.objects.select_related("role", "branch").all()
    serializer_class = UserRoleSerializer
    permission_classes = [IsRoleAdmin]
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        return scope_queryset_by_branch_access(
            queryset,
            self.request.user,
            branch_field="branch_id",
            branch_filter_id=self.request.query_params.get("branch"),
        )

    def delete(self, request, pk, **kwargs):
        instance = self.get_object()
        user_id = instance.user_id
        instance.delete()
        invalidate_user_permissions(connection.schema_name, user_id)
        return success_response(data={}, message="User role removed.")


class MyPermissionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        schema_name = connection.schema_name

        def build_payload():
            permission_map = get_user_permission_map(user)
            role_slugs = list(
                UserRole.objects.filter(user_id=user.id)
                .select_related("role")
                .values_list("role__slug", flat=True)
                .distinct()
            )
            tenant = getattr(request, "tenant", None) or getattr(user, "tenant", None)
            feature_keys: list[str] = []
            if tenant is not None and schema_name != get_public_schema_name():
                feature_keys = sorted(get_tenant_enabled_feature_keys(tenant))
            return {
                "user_id": str(user.id),
                "email": user.email,
                "full_name": getattr(user, "full_name", "") or "",
                "role_slugs": role_slugs,
                "is_tenant_admin": is_tenant_admin_user(user),
                "permissions": permission_map,
                "enabled_features": feature_keys,
            }

        if schema_name == get_public_schema_name():
            return success_response(
                data=build_payload(), message="Permissions retrieved."
            )

        payload = get_cached_value(
            access_me_key(schema_name, user.id),
            ACCESS_ME_TTL,
            build_payload,
        )
        return success_response(data=payload, message="Permissions retrieved.")


class TenantFeatureCatalogView(APIView):
    permission_classes = [IsRoleAdmin]

    def get(self, request):
        items: list[dict] = []
        seen: set[str] = set()
        for group in TENANT_REGISTRY:
            group_label = group.get("group", "")
            for item in group.get("children", []):
                key = item["key"]
                if key in seen:
                    continue
                seen.add(key)
                items.append(
                    {
                        "key": key,
                        "name": item["name"],
                        "group": group_label,
                        "parent_key": None,
                        "description": "",
                    }
                )
        return list_success_response(items=items, message="Feature catalog retrieved.")
