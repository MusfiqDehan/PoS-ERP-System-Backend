import pytest
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.branch.models import Branch
from shared.models import (
    Asset,
    AssetRelation,
    AssetRelationRole,
    AssetType,
    infer_asset_type,
)


def _make_image_file(name: str = "photo.png") -> SimpleUploadedFile:
    return SimpleUploadedFile(name, b"fake-image-bytes", content_type="image/png")


@pytest.mark.django_db
def test_asset_created_with_uuid_v7_primary_key(tenant_schema):
    asset = Asset.objects.create(
        file=_make_image_file(),
        original_filename="photo.png",
        mime_type="image/png",
        file_size=16,
        asset_type=AssetType.IMAGE,
    )
    assert asset.id is not None
    assert asset.id.version == 7


@pytest.mark.django_db
def test_asset_stores_required_metadata_fields(tenant_schema):
    asset = Asset.objects.create(
        file=_make_image_file(),
        original_filename="photo.png",
        mime_type="image/png",
        file_size=16,
        asset_type=AssetType.IMAGE,
        checksum="abc123",
        title="Product photo",
        alt_text="A product",
        description="Gallery image",
        width=800,
        height=600,
    )
    asset.refresh_from_db()
    assert asset.original_filename == "photo.png"
    assert asset.mime_type == "image/png"
    assert asset.file_size == 16
    assert asset.asset_type == AssetType.IMAGE
    assert asset.checksum == "abc123"
    assert asset.title == "Product photo"
    assert asset.alt_text == "A product"
    assert asset.description == "Gallery image"
    assert asset.width == 800
    assert asset.height == 600


@pytest.mark.django_db
def test_asset_type_choices_are_constrained(tenant_schema):
    asset = Asset(
        file=_make_image_file(),
        original_filename="notes.txt",
        mime_type="text/plain",
        file_size=4,
        asset_type="invalid",
    )
    with pytest.raises(Exception):
        asset.full_clean()


@pytest.mark.django_db
def test_asset_soft_delete(tenant_schema):
    asset = Asset.objects.create(
        file=_make_image_file(),
        original_filename="photo.png",
        mime_type="image/png",
        file_size=16,
        asset_type=AssetType.IMAGE,
    )
    asset.delete()
    asset.refresh_from_db()
    assert asset.is_deleted is True
    assert asset.deleted_at is not None
    assert Asset.objects.filter(pk=asset.pk).exists() is False
    assert Asset.all_objects.filter(pk=asset.pk).exists() is True


def _make_branch(name: str = "Main Branch", code: str = "MAIN") -> Branch:
    return Branch.objects.create(name=name, code=code)


@pytest.mark.django_db
def test_asset_relation_resolves_generic_foreign_key(tenant_schema):
    branch = _make_branch()
    asset = Asset.objects.create(
        file=_make_image_file(),
        original_filename="photo.png",
        mime_type="image/png",
        file_size=16,
        asset_type=AssetType.IMAGE,
    )
    content_type = ContentType.objects.get_for_model(Branch)
    relation = AssetRelation.objects.create(
        asset=asset,
        content_type=content_type,
        object_id=branch.id,
        role=AssetRelationRole.GALLERY,
    )
    relation.refresh_from_db()
    assert relation.content_object == branch


@pytest.mark.django_db
def test_asset_relation_stores_role_field_name_sort_order_and_primary(tenant_schema):
    branch = _make_branch(code="BR1")
    asset = Asset.objects.create(
        file=_make_image_file(),
        original_filename="photo.png",
        mime_type="image/png",
        file_size=16,
        asset_type=AssetType.IMAGE,
    )
    content_type = ContentType.objects.get_for_model(Branch)
    relation = AssetRelation.objects.create(
        asset=asset,
        content_type=content_type,
        object_id=branch.id,
        role=AssetRelationRole.PRIMARY_IMAGE,
        field_name="hero",
        sort_order=3,
        is_primary=True,
    )
    relation.refresh_from_db()
    assert relation.role == AssetRelationRole.PRIMARY_IMAGE
    assert relation.field_name == "hero"
    assert relation.sort_order == 3
    assert relation.is_primary is True


@pytest.mark.django_db
def test_asset_relation_demotes_previous_primary_for_same_slot(tenant_schema):
    branch = _make_branch(code="BR2")
    content_type = ContentType.objects.get_for_model(Branch)

    first_asset = Asset.objects.create(
        file=_make_image_file("first.png"),
        original_filename="first.png",
        mime_type="image/png",
        file_size=16,
        asset_type=AssetType.IMAGE,
    )
    second_asset = Asset.objects.create(
        file=_make_image_file("second.png"),
        original_filename="second.png",
        mime_type="image/png",
        file_size=16,
        asset_type=AssetType.IMAGE,
    )

    first_relation = AssetRelation.objects.create(
        asset=first_asset,
        content_type=content_type,
        object_id=branch.id,
        role=AssetRelationRole.PRIMARY_IMAGE,
        field_name="hero",
        is_primary=True,
    )
    second_relation = AssetRelation.objects.create(
        asset=second_asset,
        content_type=content_type,
        object_id=branch.id,
        role=AssetRelationRole.PRIMARY_IMAGE,
        field_name="hero",
        is_primary=True,
    )

    first_relation.refresh_from_db()
    second_relation.refresh_from_db()
    assert first_relation.is_primary is False
    assert second_relation.is_primary is True


@pytest.mark.parametrize(
    ("mime_type", "expected"),
    [
        ("image/png", AssetType.IMAGE),
        ("application/pdf", AssetType.PDF),
        ("video/mp4", AssetType.VIDEO),
        ("audio/mpeg", AssetType.AUDIO),
        ("text/html", AssetType.HTML),
        (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            AssetType.DOCUMENT,
        ),
        ("application/x-custom", AssetType.OTHER),
    ],
)
def test_infer_asset_type_maps_mime_types(mime_type, expected):
    assert infer_asset_type(mime_type) == expected
