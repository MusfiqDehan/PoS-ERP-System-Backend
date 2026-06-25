from rest_framework import status
from rest_framework.views import APIView

from apps.platform_owner.permissions import IsPlatformUser
from apps.tenancy.services import PlatformPermissionService
from drf_spectacular.utils import extend_schema
from shared.openapi import envelope_responses
from shared.responses import success_response
from apps.tenancy.openapi import PLATFORM_TENANCY_TAG


@extend_schema(
    tags=[PLATFORM_TENANCY_TAG],
    summary="Get effective platform permissions (legacy alias)",
    description=(
        "Legacy alias for platform permission map. Prefer "
        "GET /api/v1/platform-owner/me/permissions/. Requires platform JWT on public "
        "schema."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Permission map envelope."),
    ),
)
class PlatformPermissionsAliasView(APIView):
    permission_classes = [IsPlatformUser]

    def get(self, request):
        return success_response(
            data={"permissions": PlatformPermissionService.get_permission_map(request.user)},
            message="Permissions retrieved.",
        )
