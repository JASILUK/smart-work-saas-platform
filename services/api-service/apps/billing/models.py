from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class Plan(TimeStampedModel):

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)

    description = models.TextField(blank=True)

    # Pricing
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2)

    is_free = models.BooleanField(default=False)
    trial_days = models.PositiveIntegerField(default=0)

    # Usage Limits
    max_users = models.PositiveIntegerField(null=True, blank=True)
    max_projects = models.PositiveIntegerField(null=True, blank=True)
    max_departments = models.PositiveIntegerField(null=True, blank=True)
    max_storage_gb = models.PositiveIntegerField(default=5)
    ai_credits_per_month = models.PositiveIntegerField(default=0)

    # Feature Flags
    automation_enabled = models.BooleanField(default=False)
    advanced_analytics = models.BooleanField(default=False)
    custom_branding = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    api_access = models.BooleanField(default=False)
    custom_roles_enabled = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Subscription(TimeStampedModel):

    class Status(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        CANCELED = "canceled", "Canceled"
        EXPIRED = "expired", "Expired"
        PENDING_PAYMENT = "pending_payment", "Pending Payment"

    company = models.OneToOneField(
        "companies.Company", on_delete=models.CASCADE, related_name="subscription"
    )

    plan = models.ForeignKey("billing.Plan", on_delete=models.PROTECT)

    status = models.CharField(max_length=20, choices=Status.choices)

    billing_cycle = models.CharField(
        max_length=10,
        choices=[("monthly", "Monthly"), ("yearly", "Yearly")],
        default="monthly",
    )

    started_at = models.DateTimeField(default=timezone.now)

    trial_ends_at = models.DateTimeField(null=True, blank=True)

    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)

    provider = models.CharField(max_length=50, blank=True)
    provider_subscription_id = models.CharField(max_length=255, null=True, blank=True)
    provider_customer_id = models.CharField(max_length=255, null=True, blank=True)

    cancel_at_period_end = models.BooleanField(default=False)
