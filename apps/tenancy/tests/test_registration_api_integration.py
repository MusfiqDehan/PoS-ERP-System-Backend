"""HTTP integration tests for tenant self-registration onboarding."""

import re

import pytest
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.billing.models import Package, PackageFeature, SoftwareProduct
from apps.tenancy.models import EmailQueue, Feature, Invitation, Tenant


@pytest.fixture
def seeded_public_packages(public_schema):
    product = SoftwareProduct.objects.create(name="Sortorium PoS", slug="sortorium-pos")
    free = Package.objects.create(
        software_product=product,
        name="Free",
        slug="free",
        is_public=True,
        sort_order=0,
    )
    pro = Package.objects.create(
        software_product=product,
        name="Pro",
        slug="pro",
        is_public=True,
        sort_order=1,
    )
    dashboard = Feature.objects.create(key="dashboard", name="Dashboard")
    pos = Feature.objects.create(key="pos", name="Point of Sale")
    PackageFeature.objects.create(package=free, feature=dashboard)
    PackageFeature.objects.create(package=pro, feature=dashboard)
    PackageFeature.objects.create(package=pro, feature=pos)
    return {"free": free, "pro": pro}


def _extract_token_from_email(email: str) -> str:
    with schema_context(get_public_schema_name()):
        row = (
            EmailQueue.objects.filter(
                to_email=email,
                purpose=EmailQueue.PURPOSE_VERIFICATION,
            )
            .order_by("-created_at")
            .first()
        )
        assert row is not None
        match = re.search(r"token=([^&\s\"']+)", row.text_body)
        assert match is not None
        return match.group(1)


@pytest.mark.django_db
def test_full_registration_onboarding_flow(seeded_public_packages):
    client = APIClient()
    email = "owner@onboard.test"
    subdomain = "onboardco"

    packages_response = client.get(
        "/api/v1/billing/public/packages/", HTTP_HOST="localhost"
    )
    assert packages_response.status_code == 200
    slugs = {item["slug"] for item in packages_response.data["data"]["items"]}
    assert "pro" in slugs

    register_response = client.post(
        "/api/v1/tenancy/register/",
        {
            "subdomain": subdomain,
            "company_name": "Onboard Co",
            "admin_email": email,
            "plan": "pro",
        },
        format="json",
        HTTP_HOST="localhost",
    )
    assert register_response.status_code == 201
    assert register_response.data["success"] is True
    invitation_id = register_response.data["data"]["invitation_id"]

    with schema_context(get_public_schema_name()):
        invitation = Invitation.objects.get(pk=invitation_id)
        assert invitation.metadata.get("plan") == "pro"

    raw_token = _extract_token_from_email(email)

    validate_response = client.post(
        "/api/v1/tenancy/tokens/validate/",
        {"token": raw_token},
        format="json",
        HTTP_HOST="localhost",
    )
    assert validate_response.status_code == 200
    assert validate_response.data["data"]["token_type"] == "verification"
    assert validate_response.data["data"]["subdomain"] == subdomain

    setup_response = client.post(
        "/api/v1/tenancy/password/setup/",
        {
            "token": raw_token,
            "password": "NewPass1!",
            "confirm_password": "NewPass1!",
        },
        format="json",
        HTTP_HOST="localhost",
    )
    assert setup_response.status_code == 200
    assert setup_response.data["success"] is True
    assert setup_response.data["data"]["tenant_schema"] == subdomain.replace("-", "_")
    assert "login_url" in setup_response.data["data"]

    with schema_context(get_public_schema_name()):
        tenant = Tenant.objects.get(schema_name=subdomain.replace("-", "_"))
        assert tenant.plan == "pro"

    login_response = client.post(
        "/api/v1/tenancy/auth/login/",
        {
            "email": email,
            "password": "NewPass1!",
            "subdomain": subdomain,
        },
        format="json",
        HTTP_HOST="localhost",
    )
    assert login_response.status_code == 200
    access = login_response.data["data"]["access"]
    token = AccessToken(access)
    assert token["tenant_schema"] == subdomain.replace("-", "_")

    me_client = APIClient()
    me_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    features_response = me_client.get(
        "/api/v1/tenancy/me/features/",
        HTTP_HOST=f"{subdomain}.localhost",
    )
    assert features_response.status_code == 200
    enabled = features_response.data["data"]["features"]
    assert isinstance(enabled, list)
    assert len(enabled) > 0


@pytest.mark.django_db
def test_registration_rejects_duplicate_subdomain(seeded_public_packages):
    from apps.tenancy.models import Domain

    tenant = Tenant.objects.create(
        schema_name="existing",
        name="Existing",
        slug="existing",
        code="EXIST",
        status="active",
    )
    Domain.objects.create(domain="existing.localhost", tenant=tenant, is_primary=True)

    client = APIClient()
    response = client.post(
        "/api/v1/tenancy/register/",
        {
            "subdomain": "existing",
            "company_name": "Dup Co",
            "admin_email": "dup@co.com",
            "plan": "free",
        },
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 400
    assert response.data["success"] is False


@pytest.mark.django_db
def test_registration_rejects_unknown_plan(seeded_public_packages):
    client = APIClient()
    response = client.post(
        "/api/v1/tenancy/register/",
        {
            "subdomain": "unknownplan",
            "company_name": "Co",
            "admin_email": "owner@co.com",
            "plan": "enterprise-only",
        },
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 400
    assert "plan" in response.data["errors"]
