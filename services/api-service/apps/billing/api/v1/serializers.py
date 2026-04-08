from rest_framework import serializers

from apps.billing.models import Plan


class PlanSerializer(serializers.ModelSerializer):

    class Meta:
        model = Plan
        fields = [
            "name",
            "code",
            "price_monthly",
            "price_yearly",
            "trial_days",
            "max_users",
            "automation_enabled",
            "advanced_analytics",
            "custom_roles_enabled",
        ]


class SelectPlanSerializer(serializers.Serializer):

    plan_code = serializers.CharField()
    billing_cycle = serializers.ChoiceField(choices=["monthly", "yearly"])
