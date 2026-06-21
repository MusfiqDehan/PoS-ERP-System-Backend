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
from shared.services.asset_attachment import serialize_asset_summary


@public_post_schema(
    request=TenantAuthSerializer,
    summary="Authenticate a tenant user",
    description=(
        "Authenticates a tenant user on the public schema using email, password, and "
        "tenant domain or subdomain. Returns JWT access and refresh tokens plus tenant "
        "metadata on success. Rate limited to 30 requests per minute."
    ),
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
        tenant_payload = {
            "id": str(tokens.tenant.id),
            "name": tokens.tenant.name,
            "schema_name": tokens.tenant.schema_name,
            "domain": tokens.domain,
        }
        company_logo = serialize_asset_summary(tokens.tenant.get_company_logo_asset())
        if company_logo is not None:
            tenant_payload["company_logo"] = company_logo
        return success_response(
            data={
                "access": tokens.access,
                "refresh": tokens.refresh,
                "tenant": tenant_payload,
            },
            message="Login successful.",
        )


@public_post_schema(
    request=TokenRefreshSerializer,
    summary="Refresh JWT access token",
    description=(
        "Exchanges a valid refresh token for a new access token pair. No authentication "
        "header is required; supply the refresh token in the request body."
    ),
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
    description=(
        "Returns the authenticated user's profile within the resolved tenant schema. "
        "Requires a valid JWT bearer token."
    ),
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
    description=(
        "Changes the password for the currently authenticated tenant user. Requires the "
        "current password and a validated new password."
    ),
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
