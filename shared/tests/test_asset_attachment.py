"""Tests for AssetAttachmentService."""

import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django_tenants.utils import get_public_schema_name, schema_context

from apps.tenancy.models import Tenant, User
from shared.models import AssetRelation, AssetRelationRole, AssetType
from shared.services.asset_attachment import (
    AssetAttachmentError,
    AssetAttachmentService,
    TENANT_COMPANY_LOGO_FIELD,
    TENANT_COMPANY_LOGO_ROLE,
    USER_PROFILE_PICTURE_FIELD,
    USER_PROFILE_PICTURE_ROLE,
    serialize_asset_summary,
)


def _image(name: str = "avatar.png") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, b"image-bytes", content_type="image/png")


def _pdf(name: str = "doc.pdf") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, b"pdf-bytes", content_type="application/pdf")


@pytest.mark.django_db
def test_attach_image_to_user_creates_asset_relation(tenant_schema, tenant_user):
    relation = AssetAttachmentService.attach_image(
        file=_image(),
        parent=tenant_user,
        role=USER_PROFILE_PICTURE_ROLE,
        field_name=USER_PROFILE_PICTURE_FIELD,
        actor=tenant_user,
    )
    assert relation.is_primary is True
    assert relation.role == AssetRelationRole.AVATAR
    assert relation.field_name == USER_PROFILE_PICTURE_FIELD
    assert relation.asset.asset_type == AssetType.IMAGE
    assert tenant_user.get_profile_picture_asset() == relation.asset


@pytest.mark.django_db
def test_attach_image_replaces_primary_profile_picture(tenant_schema, tenant_user):
    first = AssetAttachmentService.attach_image(
        file=_image("first.png"),
        parent=tenant_user,
        role=USER_PROFILE_PICTURE_ROLE,
        field_name=USER_PROFILE_PICTURE_FIELD,
    )
    second = AssetAttachmentService.attach_image(
        file=_image("second.png"),
        parent=tenant_user,
        role=USER_PROFILE_PICTURE_ROLE,
        field_name=USER_PROFILE_PICTURE_FIELD,
    )
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_primary is False
    assert second.is_primary is True
    assert tenant_user.get_profile_picture_asset() == second.asset


@pytest.mark.django_db
def test_attach_image_rejects_non_image(tenant_schema, tenant_user):
    with pytest.raises(AssetAttachmentError, match="image"):
        AssetAttachmentService.attach_image(
            file=_pdf(),
            parent=tenant_user,
            role=USER_PROFILE_PICTURE_ROLE,
            field_name=USER_PROFILE_PICTURE_FIELD,
        )


@pytest.mark.django_db
def test_remove_primary_profile_picture(tenant_schema, tenant_user):
    AssetAttachmentService.attach_image(
        file=_image(),
        parent=tenant_user,
        role=USER_PROFILE_PICTURE_ROLE,
        field_name=USER_PROFILE_PICTURE_FIELD,
    )
    AssetAttachmentService.remove_primary(
        parent=tenant_user,
        role=USER_PROFILE_PICTURE_ROLE,
        field_name=USER_PROFILE_PICTURE_FIELD,
    )
    assert tenant_user.get_profile_picture_asset() is None


@pytest.mark.django_db
def test_attach_company_logo_uses_public_schema(tenant, public_schema):
    with schema_context(get_public_schema_name()):
        relation = AssetAttachmentService.attach_image(
            file=_image("logo.png"),
            parent=tenant,
            role=TENANT_COMPANY_LOGO_ROLE,
            field_name=TENANT_COMPANY_LOGO_FIELD,
        )
        assert AssetRelation.objects.filter(pk=relation.pk).exists()
    assert tenant.get_company_logo_asset() == relation.asset


@pytest.mark.django_db
def test_remove_company_logo(tenant, public_schema):
    AssetAttachmentService.attach_image(
        file=_image("logo.png"),
        parent=tenant,
        role=TENANT_COMPANY_LOGO_ROLE,
        field_name=TENANT_COMPANY_LOGO_FIELD,
    )
    AssetAttachmentService.remove_primary(
        parent=tenant,
        role=TENANT_COMPANY_LOGO_ROLE,
        field_name=TENANT_COMPANY_LOGO_FIELD,
    )
    assert tenant.get_company_logo_asset() is None


def test_serialize_asset_summary_shape():
    class _File:
        url = "/media/assets/image/example.png"

    class _Asset:
        id = "019ee000-0000-7000-8000-000000000001"
        is_deleted = False
        mime_type = "image/png"
        original_filename = "avatar.png"
        alt_text = "Avatar"
        file = _File()

    payload = serialize_asset_summary(_Asset())
    assert payload == {
        "id": "019ee000-0000-7000-8000-000000000001",
        "url": "/media/assets/image/example.png",
        "mime_type": "image/png",
        "original_filename": "avatar.png",
        "alt_text": "Avatar",
    }


def test_serialize_asset_summary_returns_none_for_missing_asset():
    assert serialize_asset_summary(None) is None


@pytest.mark.django_db
def test_get_primary_asset_filters_by_content_type(tenant_schema, tenant_user):
    AssetAttachmentService.attach_image(
        file=_image(),
        parent=tenant_user,
        role=USER_PROFILE_PICTURE_ROLE,
        field_name=USER_PROFILE_PICTURE_FIELD,
    )
    user_ct = ContentType.objects.get_for_model(User)
    assert (
        AssetRelation.objects.filter(
            content_type=user_ct,
            object_id=tenant_user.id,
            role=USER_PROFILE_PICTURE_ROLE,
            field_name=USER_PROFILE_PICTURE_FIELD,
            is_primary=True,
            is_deleted=False,
        ).count()
        == 1
    )
