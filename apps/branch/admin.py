from django.contrib import admin

from apps.branch.models import Branch


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_headquarters", "is_active")
    search_fields = ("name", "code")
