from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.tenancy.openapi import (
    TENANT_TENANCY_TAG,
    envelope_responses,
    public_post_schema,
)
from apps.tenancy.serializers import (
    ChangePasswordSerializer,
    TenantAuthSerializer,
    TokenRefreshSerializer,
    UserProfileSerializer,
)
from apps.tenancy.services import AuthService, PasswordService, TenantAuditService
from drf_spectacular.utils import OpenApiResponse, extend_schema
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode


@public_post_schema(
    request=TenantAuthSerializer,
    summary="Authenticate a tenant user",
    responses=envelope_responses(
        (
            status.HTTP_200_OK,
            "Login successful; returns JWT access and refresh tokens.",
        ),
        (status.HTTP_401_UNAUTHORIZED, "Invalid credentials."),
        (status.HTTP_403_FORBIDDEN, "Tenant access denied."),
    ),
)
class TenantAuthenticationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "tenant_auth"

    def post(self, request):
        serializer = TenantAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        try:
            tokens = AuthService.login(
                email=payload["email"],
                password=payload["password"],
                domain=payload["domain"],
                subdomain=payload["subdomain"],
                request=request,
            )
        except PermissionError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.PERMISSION_DENIED),
                http_status=status.HTTP_403_FORBIDDEN,
            )
        except ValueError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.INVALID_CREDENTIALS),
                http_status=status.HTTP_401_UNAUTHORIZED,
            )

        TenantAuditService.log(
            request=request,
            action="tenant.auth.login",
            tenant=tokens.tenant,
            target_type="user",
            target_id=tokens.user.id,
            metadata={"email": payload["email"], "domain": tokens.domain},
        )
        return success_response(
            data={
                "access": tokens.access,
                "refresh": tokens.refresh,
                "tenant": {
                    "id": str(tokens.tenant.id),
                    "name": tokens.tenant.name,
                    "schema_name": tokens.tenant.schema_name,
                    "domain": tokens.domain,
                },
            },
            message="Login successful.",
        )


@public_post_schema(
    request=TokenRefreshSerializer,
    summary="Refresh JWT access token",
    responses=envelope_responses(
        (status.HTTP_200_OK, "Token refreshed."),
        (status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token."),
    ),
)
class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            tokens = AuthService.refresh(serializer.validated_data["refresh"])
        except Exception:
            return error_response(
                message="Invalid or expired refresh token.",
                error_code=str(ErrorCode.TOKEN_EXPIRED),
                http_status=status.HTTP_401_UNAUTHORIZED,
            )
        return success_response(data=tokens, message="Token refreshed.")


@extend_schema(
    tags=[TENANT_TENANCY_TAG],
    summary="Get current tenant user profile",
    responses={
        status.HTTP_200_OK: OpenApiResponse(
            description="Authenticated user profile envelope."
        ),
    },
)
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return success_response(
            data=UserProfileSerializer(request.user).data,
            message="Profile retrieved.",
        )


@extend_schema(
    tags=[TENANT_TENANCY_TAG],
    summary="Change password for the authenticated user",
    request=ChangePasswordSerializer,
    responses=envelope_responses(
        (status.HTTP_200_OK, "Password changed successfully."),
        (status.HTTP_400_BAD_REQUEST, "Validation error."),
    ),
)
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            PasswordService.change_password(
                user=request.user,
                current_password=serializer.validated_data["current_password"],
                new_password=serializer.validated_data["new_password"],
            )
        except ValueError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data={}, message="Password changed successfully.")
