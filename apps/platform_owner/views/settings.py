from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from apps.platform_owner.openapi import PLATFORM_OWNER_TAG, envelope_responses
from apps.platform_owner.serializers import PlatformSettingsSerializer
from apps.tenancy.models import PlatformSettings
from apps.tenancy.permissions import IsPlatformFeaturePermission
from shared.openapi import document_crud_view
from shared.views import ModelCRUDView


@document_crud_view(
    tags=[PLATFORM_OWNER_TAG],
    operations={
        "GET": {
            "summary": "Read platform settings",
            "description": (
                "Returns the PlatformSettings singleton. Creates defaults if missing. "
                "Requires platform.settings view permission."
            ),
            "responses": envelope_responses(
                (status.HTTP_200_OK, "Platform settings envelope."),
            ),
        },
        "PATCH": {
            "summary": "Update platform settings",
            "description": (
                "Partially updates the PlatformSettings singleton. Requires "
                "platform.settings edit permission."
            ),
            "request": PlatformSettingsSerializer,
            "responses": envelope_responses(
                (status.HTTP_200_OK, "Updated platform settings envelope."),
                (status.HTTP_400_BAD_REQUEST, "Validation error."),
            ),
        },
    },
)
class PlatformSettingsView(ModelCRUDView):
    queryset = PlatformSettings.objects.all()
    serializer_class = PlatformSettingsSerializer
    pagination_class = None

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsPlatformFeaturePermission.require("platform.settings", "edit")()]
        return [IsPlatformFeaturePermission.require("platform.settings", "view")()]

    def get_object(self):
        return PlatformSettings.get_solo()

    def get(self, request: Request, **kwargs) -> Response:
        return self._retrieve(None)

    def patch(self, request: Request, **kwargs) -> Response:
        return self._update(None, request, partial=True)

    def get_success_message(self, action: str) -> str:
        if action == "update":
            return "Platform settings updated."
        return "Platform settings retrieved."
