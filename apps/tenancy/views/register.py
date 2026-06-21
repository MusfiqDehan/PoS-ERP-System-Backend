from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.tenancy.openapi import envelope_responses, public_post_schema
from apps.tenancy.serializers import TenantSelfRegistrationSerializer
from apps.tenancy.services import TenantRegistrationService
from shared.responses import error_response, success_response
from shared.responses.error_codes import ErrorCode


@public_post_schema(
    request=TenantSelfRegistrationSerializer,
    summary="Register a new tenant (self-service)",
    description=(
        "Starts self-service tenant registration on the public schema. Creates a pending "
        "tenant workspace and sends a verification email. Rate limited to 10 requests "
        "per hour."
    ),
    responses=envelope_responses(
        (status.HTTP_201_CREATED, "Registration accepted; verification email sent."),
        (status.HTTP_400_BAD_REQUEST, "Validation or subdomain conflict error."),
    ),
)
class TenantSelfRegistrationView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "tenant_registration"

    def post(self, request):
        serializer = TenantSelfRegistrationSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        try:
            _, invitation, domain = TenantRegistrationService.start_self_registration(
                subdomain=payload["subdomain"],
                company_name=payload["company_name"],
                admin_email=payload["admin_email"],
                admin_full_name=payload.get("admin_full_name", ""),
                contact_phone=payload.get("contact_phone", ""),
                plan=payload.get("plan", "free"),
                request=request,
            )
        except ValueError as exc:
            return error_response(
                message=str(exc),
                error_code=str(ErrorCode.VALIDATION_ERROR),
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        return success_response(
            data={
                "pending_tenant": {
                    "company_name": payload["company_name"],
                    "subdomain": payload["subdomain"],
                    "domain": domain,
                },
                "invitation_id": str(invitation.id),
            },
            message="Registration received. Check your email to verify and set your password.",
            http_status=status.HTTP_201_CREATED,
        )
