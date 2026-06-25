from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from apps.platform_owner.openapi import PLATFORM_OWNER_TAG, envelope_responses
from apps.platform_owner.serializers import PlatformFeatureSerializer
from apps.platform_owner.services import PlatformFeatureService
from apps.tenancy.permissions import IsPlatformFeaturePermission
from drf_spectacular.utils import OpenApiResponse
from shared.openapi import document_crud_view
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode
from shared.views import ModelCRUDView


@document_crud_view(
    tags=[PLATFORM_OWNER_TAG],
    operations={
        "GET": {
            "summary": "List platform feature registry",
            "description": (
                "Returns all feature definitions in the platform registry. Requires "
                "platform.features view permission."
            ),
            "responses": {
                status.HTTP_200_OK: OpenApiResponse(
                    description="Feature list envelope."
                ),
            },
        },
        "POST": {
            "summary": "Create platform feature definition",
            "description": (
                "Creates a new feature registry entry. Requires platform.features edit "
                "permission."
            ),
            "request": PlatformFeatureSerializer,
            "responses": envelope_responses(
                (status.HTTP_201_CREATED, "Feature created."),
                (status.HTTP_400_BAD_REQUEST, "Validation error."),
            ),
        },
    },
)
class PlatformFeatureListCreateView(ModelCRUDView):
    serializer_class = PlatformFeatureSerializer
    pagination_class = None

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsPlatformFeaturePermission.require("platform.features", "edit")()]
        return [IsPlatformFeaturePermission.require("platform.features", "view")()]

    def get_queryset(self):
        return PlatformFeatureService.list_features()

    def get_success_message(self, action: str) -> str:
        if action == "create":
            return "Feature created."
        return "Features retrieved."

    def _create(self, request: Request) -> Response:
        serializer = PlatformFeatureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            feature = PlatformFeatureService.create_feature(
                data=dict(serializer.validated_data)
            )
        except ValueError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(
            data=PlatformFeatureSerializer(feature).data,
            message=self.get_success_message("create"),
            http_status=status.HTTP_201_CREATED,
        )


@document_crud_view(
    tags=[PLATFORM_OWNER_TAG],
    operations={
        "PATCH": {
            "summary": "Update platform feature definition",
            "description": (
                "Partially updates a feature registry entry. System features cannot "
                "change key or scope. Requires platform.features edit permission."
            ),
            "request": PlatformFeatureSerializer,
            "responses": envelope_responses(
                (status.HTTP_200_OK, "Feature updated."),
                (status.HTTP_400_BAD_REQUEST, "Validation error."),
                (status.HTTP_404_NOT_FOUND, "Feature not found."),
            ),
        },
    },
)
class PlatformFeatureDetailView(ModelCRUDView):
    serializer_class = PlatformFeatureSerializer
    permission_classes = [
        IsPlatformFeaturePermission.require("platform.features", "edit")
    ]
    lookup_field = "key"
    lookup_url_kwarg = "feature_key"

    def get_queryset(self):
        return PlatformFeatureService.list_features()

    def get_success_message(self, action: str) -> str:
        return "Feature updated."

    def patch(self, request, feature_key, **kwargs):
        return self._update(feature_key, request, partial=True)

    def _update(self, pk, request: Request, partial: bool) -> Response:
        feature = self.get_object()
        serializer = PlatformFeatureSerializer(
            feature, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        try:
            updated = PlatformFeatureService.update_feature(
                feature, data=dict(serializer.validated_data)
            )
        except ValueError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(
            data=PlatformFeatureSerializer(updated).data,
            message=self.get_success_message("update"),
        )
