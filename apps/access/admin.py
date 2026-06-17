from django.contrib import admin

from apps.access.models import Role, RolePermission, UserRole


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_system", "color")
    search_fields = ("name", "slug")
    list_filter = ("is_system",)


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "feature_key", "permission_level")
    list_filter = ("permission_level",)
    search_fields = ("feature_key",)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user_email", "role", "branch", "created_at")
    search_fields = ("user_email",)
    list_filter = ("role",)
