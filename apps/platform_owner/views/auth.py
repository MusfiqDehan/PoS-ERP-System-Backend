from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.platform_owner.openapi import PLATFORM_OWNER_TAG, envelope_responses, public_post_schema
from apps.platform_owner.permissions import IsPlatformUser
from apps.platform_owner.serializers import (
    PlatformAuthSerializer,
    PlatformPasswordConfirmSerializer,
    PlatformPasswordResetRequestSerializer,
    PlatformTokenRefreshSerializer,
)
from apps.platform_owner.services.auth import PlatformAuthService
from apps.platform_owner.services.password import PlatformPasswordService
from apps.tenancy.serializers import ChangePasswordSerializer, UserProfileSerializer
from apps.tenancy.services import PasswordService, PlatformPermissionService
from drf_spectacular.utils import OpenApiResponse, extend_schema
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode


@public_post_schema(
    request=PlatformAuthSerializer,
    summary="Authenticate a platform owner user",
    description=(
        "Authenticates a platform team member on the public schema using email and "
        "password. Access is invite-only; users must accept a platform invitation "
        "before logging in. Returns JWT tokens with platform_user claim. Rate limited."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Login successful."),
        (status.HTTP_401_UNAUTHORIZED, "Invalid credentials."),
        (status.HTTP_403_FORBIDDEN, "Platform access denied."),
    ),
)
class PlatformAuthenticationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "platform_auth"

    def post(self, request):
        serializer = PlatformAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        try:
            tokens = PlatformAuthService.login(
                email=payload["email"],
                password=payload["password"],
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
        return success_response(
            data={
                "access": tokens.access,
                "refresh": tokens.refresh,
                "user": PlatformAuthService.serialize_user(tokens.user),
            },
            message="Login successful.",
        )


@public_post_schema(
    request=PlatformTokenRefreshSerializer,
    summary="Refresh platform owner JWT access token",
    description=(
        "Exchanges a valid platform refresh token (platform_user claim) for new "
        "access and refresh tokens. No authentication header required."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Token refreshed."),
        (status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token."),
    ),
)
class PlatformTokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PlatformTokenRefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            tokens = PlatformAuthService.refresh(serializer.validated_data["refresh"])
        except Exception:
            return error_response(
                message="Invalid or expired refresh token.",
                error_code=str(ErrorCode.TOKEN_EXPIRED),
                http_status=status.HTTP_401_UNAUTHORIZED,
            )
        return success_response(data=tokens, message="Token refreshed.")


@extend_schema(
    tags=[PLATFORM_OWNER_TAG],
    summary="Get current platform owner profile",
    description=(
        "Returns the authenticated platform user's profile from the public schema. "
        "Requires a platform JWT (platform_user claim). Invite-only; no registration."
    ),
    responses={
        status.HTTP_200_OK: OpenApiResponse(description="Platform user profile envelope."),
    },
)
class PlatformMeView(APIView):
    permission_classes = [IsPlatformUser]

    def get(self, request):
        return success_response(
            data=UserProfileSerializer(request.user).data,
            message="Profile retrieved.",
        )


@extend_schema(
    tags=[PLATFORM_OWNER_TAG],
    summary="Get effective platform permissions",
    description=(
        "Returns the effective platform permission map for the authenticated platform "
        "user via PlatformPermissionService."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Permission map envelope."),
    ),
)
class PlatformPermissionsView(APIView):
    permission_classes = [IsPlatformUser]

    def get(self, request):
        return success_response(
            data={"permissions": PlatformPermissionService.get_permission_map(request.user)},
            message="Permissions retrieved.",
        )


@extend_schema(
    tags=[PLATFORM_OWNER_TAG],
    summary="Change password for authenticated platform user",
    description=(
        "Changes the password for the currently authenticated platform user. Requires "
        "the current password and a validated new password."
    ),
    request=ChangePasswordSerializer,
    responses=envelope_responses(
        (status.HTTP_200_OK, "Password changed successfully."),
        (status.HTTP_400_BAD_REQUEST, "Validation error."),
    ),
)
class PlatformChangePasswordView(APIView):
    permission_classes = [IsPlatformUser]

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


@public_post_schema(
    request=PlatformPasswordResetRequestSerializer,
    summary="Request platform password reset email",
    description=(
        "Requests a password reset email for a platform user. Always returns a generic "
        "success message. Rate limited."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Generic success regardless of account existence."),
    ),
)
class PlatformPasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "platform_password_reset"

    def post(self, request):
        serializer = PlatformPasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PlatformPasswordService.request_reset(email=serializer.validated_data["email"])
        return success_response(
            data={},
            message="If the account exists, reset instructions were sent.",
        )


@public_post_schema(
    request=PlatformPasswordConfirmSerializer,
    summary="Confirm platform password reset",
    description=(
        "Sets a new password using a valid platform password reset token issued on "
        "the public schema."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Password reset successful."),
        (status.HTTP_400_BAD_REQUEST, "Invalid token or validation error."),
    ),
)
class PlatformPasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "platform_password_setup"

    def post(self, request):
        serializer = PlatformPasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            PlatformPasswordService.confirm_reset(
                raw_token=serializer.validated_data["token"],
                password=serializer.validated_data["password"],
            )
        except ValueError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(data={}, message="Password reset successful.")
