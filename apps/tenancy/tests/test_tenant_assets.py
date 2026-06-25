"""Tests for tenant profile pictures and company logos."""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django_tenants.utils import schema_context
from rest_framework.test import APIClient

from apps.access.models import Role, UserRole
from apps.tenancy.serializers import TenantBrandingSerializer, UserProfileSerializer
from apps.tenancy.serializers.tenant_user import TenantUserListSerializer
from shared.services.asset_attachment import (
    AssetAttachmentService,
    TENANT_COMPANY_LOGO_FIELD,
    TENANT_COMPANY_LOGO_ROLE,
    USER_PROFILE_PICTURE_FIELD,
    USER_PROFILE_PICTURE_ROLE,
)


def _image(name: str = "avatar.png") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, b"image-bytes", content_type="image/png")


def _pdf(name: str = "doc.pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, b"pdf-bytes", content_type="application/pdf")


@pytest.mark.django_db
def test_user_profile_serializer_includes_profile_picture(tenant_schema, tenant_user):
    AssetAttachmentService.attach_image(
        file=_image(),
        parent=tenant_user,
        role=USER_PROFILE_PICTURE_ROLE,
        field_name=USER_PROFILE_PICTURE_FIELD,
    )
    payload = UserProfileSerializer(tenant_user).data
    assert payload["profile_picture"]["mime_type"] == "image/png"
    assert payload["profile_picture"]["original_filename"] == "avatar.png"


@pytest.mark.django_db
def test_user_profile_serializer_null_profile_picture(tenant_schema, tenant_user):
    payload = UserProfileSerializer(tenant_user).data
    assert payload.get("profile_picture") is None


@pytest.mark.django_db
def test_tenant_user_list_serializer_includes_profile_picture(
    tenant_schema, tenant_user
):
    AssetAttachmentService.attach_image(
        file=_image(),
        parent=tenant_user,
        role=USER_PROFILE_PICTURE_ROLE,
        field_name=USER_PROFILE_PICTURE_FIELD,
    )
    asset_map = {tenant_user.id: tenant_user.get_profile_picture_asset()}
    payload = TenantUserListSerializer(
        tenant_user,
        context={"profile_picture_assets": asset_map},
    ).data
    assert payload["profile_picture"]["original_filename"] == "avatar.png"


@pytest.mark.django_db
def test_tenant_branding_serializer_includes_company_logo(tenant, public_schema):
    AssetAttachmentService.attach_image(
        file=_image("logo.png"),
        parent=tenant,
        role=TENANT_COMPANY_LOGO_ROLE,
        field_name=TENANT_COMPANY_LOGO_FIELD,
    )
    payload = TenantBrandingSerializer(tenant).data
    assert payload["company_logo"]["original_filename"] == "logo.png"


@pytest.mark.django_db
def test_profile_picture_upload_and_delete(
    tenant, tenant_domain, tenant_schema, tenant_user
):
    client = APIClient()
    client.force_authenticate(user=tenant_user)
    upload = client.put(
        "/api/v1/tenancy/me/profile-picture/",
        {"file": _image()},
        format="multipart",
        HTTP_HOST="test-tenant.localhost",
    )
    assert upload.status_code == 200
    assert upload.data["data"]["profile_picture"]["mime_type"] == "image/png"

    me = client.get("/api/v1/tenancy/me/", HTTP_HOST="test-tenant.localhost")
    assert me.data["data"]["profile_picture"]["mime_type"] == "image/png"

    delete = client.delete(
        "/api/v1/tenancy/me/profile-picture/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert delete.status_code == 200
    me_after_delete = client.get(
        "/api/v1/tenancy/me/", HTTP_HOST="test-tenant.localhost"
    )
    assert me_after_delete.data["data"].get("profile_picture") is None


@pytest.mark.django_db
def test_profile_picture_upload_rejects_non_image(
    tenant, tenant_domain, tenant_schema, tenant_user
):
    client = APIClient()
    client.force_authenticate(user=tenant_user)
    response = client.put(
        "/api/v1/tenancy/me/profile-picture/",
        {"file": _pdf()},
        format="multipart",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_profile_picture_upload_requires_authentication(tenant, tenant_domain):
    client = APIClient()
    response = client.put(
        "/api/v1/tenancy/me/profile-picture/",
        {"file": _image()},
        format="multipart",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_tenant_branding_logo_endpoints(tenant, tenant_domain, tenant_schema):
    User = get_user_model()
    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        admin = User.objects.create_user(email="admin@test.com", password="TestPass1!")
        admin_role = Role.objects.create(name="Admin", slug="admin", is_system=True)
        UserRole.objects.create(
            user_id=admin.id,
            user_email=admin.email,
            role=admin_role,
        )

    client = APIClient()
    client.force_authenticate(user=admin)

    upload = client.put(
        "/api/v1/tenancy/settings/branding/logo/",
        {"file": _image("logo.png")},
        format="multipart",
        HTTP_HOST="test-tenant.localhost",
    )
    assert upload.status_code == 200
    assert upload.data["data"]["company_logo"]["original_filename"] == "logo.png"

    branding = client.get(
        "/api/v1/tenancy/settings/branding/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert branding.status_code == 200
    assert branding.data["data"]["company_logo"]["original_filename"] == "logo.png"

    delete = client.delete(
        "/api/v1/tenancy/settings/branding/logo/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert delete.status_code == 200
    branding_after_delete = client.get(
        "/api/v1/tenancy/settings/branding/",
        HTTP_HOST="test-tenant.localhost",
    )
    assert branding_after_delete.data["data"].get("company_logo") is None


@pytest.mark.django_db
def test_tenant_branding_logo_requires_permission(tenant, tenant_domain, tenant_schema):
    User = get_user_model()
    with schema_context(tenant.schema_name):
        connection.set_tenant(tenant)
        cashier = User.objects.create_user(
            email="cashier@test.com", password="TestPass1!"
        )
        cashier_role = Role.objects.create(
            name="Cashier", slug="cashier", is_system=True
        )
        UserRole.objects.create(
            user_id=cashier.id,
            user_email=cashier.email,
            role=cashier_role,
        )

    client = APIClient()
    client.force_authenticate(user=cashier)
    response = client.put(
        "/api/v1/tenancy/settings/branding/logo/",
        {"file": _image("logo.png")},
        format="multipart",
        HTTP_HOST="test-tenant.localhost",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_login_includes_company_logo_when_configured(
    tenant, tenant_domain, tenant_user, public_schema
):
    AssetAttachmentService.attach_image(
        file=_image("logo.png"),
        parent=tenant,
        role=TENANT_COMPANY_LOGO_ROLE,
        field_name=TENANT_COMPANY_LOGO_FIELD,
    )
    client = APIClient()
    response = client.post(
        "/api/v1/tenancy/auth/login/",
        {
            "email": "user@test.com",
            "password": "TestPass1!",
            "domain": "test-tenant.localhost",
        },
        format="json",
        HTTP_HOST="localhost",
    )
    assert response.status_code == 200
    assert (
        response.data["data"]["tenant"]["company_logo"]["original_filename"]
        == "logo.png"
    )
