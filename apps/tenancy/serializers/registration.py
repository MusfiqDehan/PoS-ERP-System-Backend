import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework import serializers

from apps.tenancy.models import Domain, Invitation
from apps.billing.services.public_catalog import public_package_slugs
from apps.tenancy.services.registration import (
    full_domain_for_subdomain,
    normalize_subdomain,
)

SUBDOMAIN_RE = re.compile(r"^(?!-)[a-z0-9-]{3,63}(?<!-)$")


class TenantSelfRegistrationSerializer(serializers.Serializer):
    subdomain = serializers.CharField(max_length=63)
    company_name = serializers.CharField(max_length=255)
    admin_email = serializers.EmailField()
    admin_full_name = serializers.CharField(
        max_length=120, required=False, allow_blank=True
    )
    contact_phone = serializers.CharField(
        max_length=30, required=False, allow_blank=True
    )

    def validate_subdomain(self, value):
        normalized = normalize_subdomain(value)
        if not SUBDOMAIN_RE.match(normalized):
            raise serializers.ValidationError(
                "Subdomain must be 3-63 chars, lowercase letters/numbers/hyphens."
            )
        request = self.context.get("request")
        domain_value = full_domain_for_subdomain(normalized, request=request)
        with schema_context(get_public_schema_name()):
            exists = Domain.objects.filter(domain=domain_value).exists()
            pending = Invitation.objects.filter(
                token_type__in=[
                    Invitation.TOKEN_TYPE_VERIFICATION,
                    Invitation.TOKEN_TYPE_INVITATION,
                ],
                subdomain=normalized,
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).exists()
        if exists and not self.context.get("allow_existing_subdomain", False):
            raise serializers.ValidationError("This subdomain is already in use.")
        if pending and not self.context.get("allow_existing_subdomain", False):
            raise serializers.ValidationError(
                "This subdomain already has a pending invitation."
            )
        return normalized

    def validate_admin_email(self, value):
        try:
            validate_email(value)
        except DjangoValidationError:
            raise serializers.ValidationError("Enter a valid email address.")
        return value.lower().strip()

    plan = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default="free"
    )

    def validate(self, attrs):
        plan = (attrs.get("plan") or "").strip().lower() or "free"
        allowed = public_package_slugs()
        if plan not in allowed:
            raise serializers.ValidationError(
                {"plan": ["Select a valid subscription plan."]}
            )
        attrs["plan"] = plan
        return attrs
