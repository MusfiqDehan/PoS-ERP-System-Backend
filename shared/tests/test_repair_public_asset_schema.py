"""Tests for public-schema shared asset repair command."""

import pytest
from django.core.management import call_command
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context

from shared.management.commands.repair_public_asset_schema import (
    clear_public_shared_migration_records,
    public_shared_asset_tables_exist,
)


@pytest.mark.django_db
def test_public_shared_asset_tables_exist(public_schema):
    assert public_shared_asset_tables_exist() is True


@pytest.mark.django_db
def test_repair_public_asset_schema_is_idempotent(public_schema):
    call_command("repair_public_asset_schema")
    assert public_shared_asset_tables_exist() is True


@pytest.mark.django_db
def test_repair_public_asset_schema_recreates_missing_tables(public_schema):
    with schema_context(get_public_schema_name()):
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS shared_asset_relation CASCADE")
            cursor.execute("DROP TABLE IF EXISTS shared_asset CASCADE")
    clear_public_shared_migration_records()

    call_command("repair_public_asset_schema")
    assert public_shared_asset_tables_exist() is True
