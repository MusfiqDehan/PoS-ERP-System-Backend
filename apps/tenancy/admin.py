from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.tenancy.models import (
    Domain,
    EmailQueue,
    Feature,
    Invitation,
    PlatformRole,
    PlatformRolePermission,
    PlatformSettings,
    PlatformUserRole,
    Tenant,
    TenantAuditLog,
    User,
)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "schema_name", "slug", "status", "is_enabled", "plan")
    search_fields = ("name", "schema_name", "slug", "owner_email")
    list_filter = ("status", "is_enabled", "plan")


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "tenant", "is_primary")
    search_fields = ("domain",)
    list_filter = ("is_primary",)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("email",)
    list_display = (
        "email",
        "full_name",
        "is_staff",
        "is_superuser",
        "is_active",
        "tenant",
    )
    search_fields = ("email", "full_name", "phone")
    fieldsets = (
        (None, {"fields": ("email", "phone", "password")}),
        (
            "Profile",
            {"fields": ("full_name", "tenant", "email_verified", "password_set_at")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Dates", {"fields": ("last_login", "created_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )
    readonly_fields = ("created_at", "password_set_at", "last_login")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "token_type",
        "subdomain",
        "company_name",
        "expires_at",
        "used_at",
    )
    search_fields = ("email", "subdomain", "company_name")
    list_filter = ("token_type",)


@admin.register(EmailQueue)
class EmailQueueAdmin(admin.ModelAdmin):
    list_display = (
        "to_email",
        "purpose",
        "status",
        "attempts",
        "created_at",
        "sent_at",
    )
    list_filter = ("status", "purpose")
    search_fields = ("to_email", "subject")


@admin.register(TenantAuditLog)
class TenantAuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "actor_email", "tenant", "target_type", "created_at")
    search_fields = ("action", "actor_email", "target_id")
    list_filter = ("action",)


@admin.register(PlatformRole)
class PlatformRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_system")
    search_fields = ("name", "slug")


@admin.register(PlatformRolePermission)
class PlatformRolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "module_key", "permission_level")
    list_filter = ("permission_level",)


@admin.register(PlatformUserRole)
class PlatformUserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "created_at")


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "scope", "sort_order", "is_system")
    search_fields = ("key", "name")
    list_filter = ("scope", "is_system")


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "default_timezone",
        "default_language",
        "default_currency",
        "updated_at",
    )
