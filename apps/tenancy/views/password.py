from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.tenancy.openapi import envelope_responses, public_post_schema
from apps.tenancy.serializers import (
    InvitationTokenSerializer,
    PasswordResetRequestSerializer,
    PasswordSetupSerializer,
)
from apps.tenancy.services import AuthService, InvitationService, PasswordService
from apps.tenancy.services.registration import full_domain_for_subdomain
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode


@public_post_schema(
    request=InvitationTokenSerializer,
    summary="Validate an invitation or verification token",
    description=(
        "Validates an invitation, email verification, or setup token on the public "
        "schema. Returns invitation metadata when the token is valid and the tenant "
        "workspace allows user entry."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Token is valid."),
        (status.HTTP_400_BAD_REQUEST, "Invalid or expired token."),
        (status.HTTP_403_FORBIDDEN, "Tenant workspace is suspended."),
    ),
)
class InvitationValidationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = InvitationTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_token = serializer.validated_data["token"]
        invitation = InvitationService.validate_token(raw_token)
        if invitation is None:
            return error_response(
                message="Invalid or expired token.",
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        tenant = invitation.tenant
        if tenant is not None and not tenant.allows_user_entry():
            return error_response(
                message="Tenant workspace is suspended.",
                error_code=str(ErrorCode.TENANT_SUSPENDED),
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return success_response(
            data=InvitationService.serialize_invitation(invitation, raw_token),
            message="Token is valid.",
        )


@public_post_schema(
    request=PasswordSetupSerializer,
    summary="Set password using invitation or verification token",
    description=(
        "Sets the initial password for a user using a valid invitation or verification "
        "token. Rate limited to 20 requests per hour."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Password configured."),
        (status.HTTP_400_BAD_REQUEST, "Invalid token or password validation error."),
    ),
)
class PasswordSetupView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "tenant_password_setup"

    def post(self, request):
        serializer = PasswordSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = PasswordService.setup_password(
                raw_token=serializer.validated_data["token"],
                password=serializer.validated_data["password"],
            )
        except ValueError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        return success_response(
            data=result, message=result.get("message", "Password configured.")
        )


@public_post_schema(
    request=PasswordResetRequestSerializer,
    summary="Request a tenant password reset email",
    description=(
        "Requests a password reset email for a tenant user. Always returns a generic "
        "success message to avoid account enumeration. Rate limited to 10 requests per "
        "hour."
    ),
    responses=envelope_responses(
        (
            status.HTTP_200_OK,
            "Generic success message regardless of account existence.",
        ),
    ),
)
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "tenant_password_reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        domain_name = payload["domain"] or full_domain_for_subdomain(
            payload["subdomain"], request=request
        )
        domain = AuthService.resolve_domain(domain=domain_name)
        message = "If the account exists, reset instructions were sent."
        if domain is None:
            return success_response(data={}, message=message)

        tenant = domain.tenant
        if not tenant.allows_user_entry():
            return success_response(data={}, message=message)

        from django.contrib.auth import get_user_model
        from django_tenants.utils import schema_context

        User = get_user_model()
        with schema_context(tenant.schema_name):
            user = User.objects.filter(email__iexact=payload["email"]).first()
        if user is None:
            return success_response(data={}, message=message)

        InvitationService.issue_password_reset(
            tenant=tenant,
            email=payload["email"],
            full_name=user.full_name,
            subdomain=payload.get("subdomain") or domain_name.split(".")[0],
            domain=domain_name,
        )
        return success_response(data={}, message=message)


@public_post_schema(
    request=PasswordSetupSerializer,
    summary="Confirm password reset using reset token",
    description=(
        "Confirms a password reset by setting a new password with a valid reset token. "
        "Uses the same payload contract as password setup. Rate limited to 20 requests "
        "per hour."
    ),
    responses=envelope_responses(
        (status.HTTP_200_OK, "Password configured."),
        (status.HTTP_400_BAD_REQUEST, "Invalid token or password validation error."),
    ),
)
class PasswordResetConfirmView(PasswordSetupView):
    """Dedicated endpoint for password-reset token confirmation."""
