from django.contrib import admin

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
class UserAdmin(admin.ModelAdmin):
    ordering = ("email",)
    list_display = (
        "email",
        "full_name",
        "is_active",
        "tenant",
        "email_verified",
        "created_at",
    )
    search_fields = ("email", "full_name", "phone")
    readonly_fields = (
        "created_at",
        "updated_at",
        "password_set_at",
        "last_login",
        "deleted_at",
    )
    fieldsets = (
        (None, {"fields": ("email", "phone", "password")}),
        (
            "Profile",
            {"fields": ("full_name", "tenant", "email_verified", "password_set_at")},
        ),
        (
            "Status",
            {
                "fields": (
                    "is_active",
                    "is_published",
                    "is_deleted",
                    "deleted_at",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                    "deleted_by",
                    "last_login",
                )
            },
        ),
    )


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
    list_display = ("to_email", "purpose", "status", "created_at", "sent_at")
    search_fields = ("to_email",)
    list_filter = ("purpose", "status")


@admin.register(TenantAuditLog)
class TenantAuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "tenant", "actor_email", "created_at")
    search_fields = ("action", "actor_email")
    list_filter = ("action",)


@admin.register(PlatformRole)
class PlatformRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_system")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(PlatformRolePermission)
class PlatformRolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "module_key", "permission_level")
    list_filter = ("module_key", "permission_level")
    search_fields = ("role__name", "module_key")


@admin.register(PlatformUserRole)
class PlatformUserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "assigned_by", "created_at")
    search_fields = ("user__email", "role__slug")
    list_filter = ("role",)


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "scope", "sort_order", "is_system")
    search_fields = ("key", "name")
    list_filter = ("scope", "is_system")


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "default_timezone", "default_language", "updated_at")
