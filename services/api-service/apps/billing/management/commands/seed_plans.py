from django.core.management.base import BaseCommand

from apps.billing.models import Plan

PLANS = [
    # =========================
    # FREE PLAN
    # =========================
    {
        "name": "Free",
        "code": "free",
        "description": "Basic plan for small teams getting started.",
        "price_monthly": 0,
        "price_yearly": 0,
        "is_free": True,
        "trial_days": 0,
        "max_users": 5,
        "max_projects": 3,
        "max_departments": 3,
        "max_storage_gb": 2,
        "ai_credits_per_month": 0,
        "automation_enabled": False,
        "advanced_analytics": False,
        "custom_branding": False,
        "priority_support": False,
        "api_access": False,
        "custom_roles_enabled": False,
        "is_active": True,
    },
    # =========================
    # STARTER PLAN
    # =========================
    {
        "name": "Starter",
        "code": "starter",
        "description": "Perfect for growing teams.",
        "price_monthly": 29,
        "price_yearly": 290,
        "is_free": False,
        "trial_days": 14,
        "max_users": 20,
        "max_projects": 20,
        "max_departments": 10,
        "max_storage_gb": 20,
        "ai_credits_per_month": 500,
        "automation_enabled": True,
        "advanced_analytics": False,
        "custom_branding": False,
        "priority_support": False,
        "api_access": False,
        "custom_roles_enabled": True,
        "is_active": True,
    },
    # =========================
    # PRO PLAN
    # =========================
    {
        "name": "Pro",
        "code": "pro",
        "description": "Advanced features for scaling businesses.",
        "price_monthly": 79,
        "price_yearly": 790,
        "is_free": False,
        "trial_days": 14,
        "max_users": 100,
        "max_projects": None,
        "max_departments": None,
        "max_storage_gb": 100,
        "ai_credits_per_month": 5000,
        "automation_enabled": True,
        "advanced_analytics": True,
        "custom_branding": True,
        "priority_support": True,
        "api_access": True,
        "custom_roles_enabled": True,
        "is_active": True,
    },
    # =========================
    # ENTERPRISE PLAN
    # =========================
    {
        "name": "Enterprise",
        "code": "enterprise",
        "description": "Custom solution for large organizations.",
        "price_monthly": 199,
        "price_yearly": 1990,
        "is_free": False,
        "trial_days": 0,
        "max_users": None,
        "max_projects": None,
        "max_departments": None,
        "max_storage_gb": 500,
        "ai_credits_per_month": 20000,
        "automation_enabled": True,
        "advanced_analytics": True,
        "custom_branding": True,
        "priority_support": True,
        "api_access": True,
        "custom_roles_enabled": True,
        "is_active": True,
    },
]


class Command(BaseCommand):

    help = "Seed subscription plans"

    def handle(self, *args, **kwargs):

        for plan_data in PLANS:
            Plan.objects.update_or_create(code=plan_data["code"], defaults=plan_data)

        self.stdout.write(self.style.SUCCESS("Plans seeded successfully."))
