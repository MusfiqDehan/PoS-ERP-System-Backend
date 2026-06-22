from rest_framework import serializers

from apps.branch.models import Branch


class BranchSerializer(serializers.ModelSerializer):
    manager_name = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = [
            "id",
            "name",
            "code",
            "is_headquarters",
            "address",
            "city",
            "location",
            "description",
            "manager",
            "manager_name",
            "phone_number",
            "email",
            "operating_hours",
            "opening_time",
            "closing_time",
            "weekdays_hours",
            "weekend_hours",
            "opening_date",
            "status",
            "capacity",
            "staff_count",
            "monthly_revenue",
            "revenue_trend",
            "rating",
            "image",
            "homepage_image",
            "website",
            "show_on_homepage",
            "is_flagship",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_manager_name(self, obj):
        if obj.manager_id and obj.manager:
            return getattr(obj.manager, "full_name", None) or obj.manager.email
        return None

    def validate_manager(self, manager):
        if manager is None:
            return manager
        from apps.branch.services.manager import validate_branch_manager_user

        branch = self.instance
        validate_branch_manager_user(manager, branch=branch)
        return manager


class BranchMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["id", "name", "code"]


class BranchSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    code = serializers.CharField()
    status = serializers.CharField()
    staff_count = serializers.IntegerField()
    user_count = serializers.IntegerField()
    monthly_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    rating = serializers.FloatField()
