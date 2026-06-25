"""Repair missing shared Asset tables on the public PostgreSQL schema."""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context


def public_shared_asset_tables_exist() -> bool:
    with schema_context(get_public_schema_name()):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'shared_asset'
                LIMIT 1
                """)
            return cursor.fetchone() is not None


def clear_public_shared_migration_records() -> int:
    with schema_context(get_public_schema_name()):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM django_migrations WHERE app = 'shared'")
            return cursor.rowcount


class Command(BaseCommand):
    help = (
        "Ensure shared Asset tables exist in the public schema. "
        "Repairs stale django_migrations rows when tables were never created."
    )

    def handle(self, *args, **options):
        if public_shared_asset_tables_exist():
            self.stdout.write("Public shared_asset tables already exist.")
            return

        deleted = clear_public_shared_migration_records()
        self.stdout.write(
            self.style.WARNING(
                f"Removed {deleted} stale shared migration record(s) from public schema."
            )
        )
        call_command(
            "migrate_schemas",
            "--shared",
            "shared",
            verbosity=options.get("verbosity", 1),
            noinput=True,
        )

        if public_shared_asset_tables_exist():
            self.stdout.write(
                self.style.SUCCESS("Public shared_asset tables are now present.")
            )
            return

        raise SystemExit("Public shared_asset tables are still missing after migrate.")
