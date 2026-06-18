from django.contrib.auth.hashers import check_password as auth_check_password
from django.contrib.auth.hashers import make_password
from django.db import models
from django.utils import timezone

from shared.models import BaseModel, SoftDeleteManager


class UserManager(SoftDeleteManager):
    def get_by_natural_key(self, username):
        return self.get(email__iexact=username)

    def create_user(self, email=None, phone=None, password=None, **extra_fields):
        if not email and not phone:
            raise ValueError("User must have either email or phone")

        if password and not extra_fields.get("password_set_at"):
            extra_fields["password_set_at"] = timezone.now()

        user = self.model(
            email=self.normalize_email(email) if email else None,
            phone=phone,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superadmin(self, email, password=None, **extra_fields):
        extra_fields.setdefault("email_verified", True)
        user = self.create_user(email=email, password=password, **extra_fields)
        from apps.tenancy.models.platform_rbac import PlatformRole, PlatformUserRole

        role, _ = PlatformRole.objects.get_or_create(
            slug="superadmin",
            defaults={
                "name": "Superadmin",
                "description": "Full platform-wide access.",
                "is_system": True,
            },
        )
        PlatformUserRole.objects.get_or_create(user=user, role=role)
        return user

    @classmethod
    def normalize_email(cls, email):
        if not email:
            return email
        return email.strip().lower()


class User(BaseModel):
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
    full_name = models.CharField(max_length=100, blank=True, default="")
    tenant = models.ForeignKey(
        "tenancy.Tenant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        help_text="Tenant this user belongs to. Platform users leave this empty.",
    )

    email_verified = models.BooleanField(default=False)
    password_set_at = models.DateTimeField(null=True, blank=True)
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        indexes = [
            models.Index(fields=["is_active"], name="idx_user_active"),
        ]

    def __str__(self) -> str:
        return f"{self.email or self.phone}"

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return auth_check_password(raw_password, self.password)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_staff(self) -> bool:
        from apps.tenancy.services.platform_permissions import PlatformPermissionService

        return PlatformPermissionService.is_superadmin(self)

    def has_perm(self, perm, obj=None):
        return self.is_staff

    def has_module_perms(self, app_label):
        return self.is_staff
