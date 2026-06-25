import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import get_public_schema_name, schema_context

from apps.tenancy.models import Tenant


def ensure_superadmin(user_model, email, password, stdout, *, tenant_fk=None):
    """Create platform superadmin if missing.

    ``tenant_fk`` is the optional User.tenant FK for tenant-scoped admins only.
    Platform owners on the public schema must keep tenant_fk=None.
    """
    user = user_model.objects.filter(email__iexact=email).first()
    if user:
        if tenant_fk is not None and user.tenant_id is None:
            user.tenant = tenant_fk
            user.save(update_fields=["tenant"])
            stdout.write(f"Linked existing superadmin to tenant: {email}")
            return
        stdout.write(f"Superadmin already exists: {email}")
        return
    user_model.objects.create_superadmin(
        email=email, password=password, tenant=tenant_fk
    )
    stdout.write(f"Created superadmin: {email}")


class Command(BaseCommand):
    help = (
        "Create the default platform superadmin account if it does not exist. "
        "Reads SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD, and SUPERADMIN_SCHEMA "
        "(PostgreSQL schema context; platform users always have tenant=NULL)."
    )

    def handle(self, *args, **options):
        email = os.environ.get("SUPERADMIN_EMAIL", "").strip()
        password = os.environ.get("SUPERADMIN_PASSWORD", "")
        if not email:
            raise CommandError("SUPERADMIN_EMAIL is not set.")
        if not password:
            raise CommandError("SUPERADMIN_PASSWORD is not set.")

        user_model = get_user_model()
        target_schema = (
            os.environ.get("SUPERADMIN_SCHEMA", "").strip() or get_public_schema_name()
        )
        tenant_fk = None
        if target_schema != get_public_schema_name():
            tenant_fk = Tenant.objects.filter(schema_name=target_schema).first()

        with schema_context(target_schema):
            ensure_superadmin(
                user_model,
                email,
                password,
                self.stdout,
                tenant_fk=tenant_fk,
            )
