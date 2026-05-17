import uuid

from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.users.models import User


class Company(TimeStampedModel):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    name = models.CharField(
        max_length=255,
    )

    slug = models.SlugField(
        unique=True,
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="owned_companies",
    )

    logo = models.ImageField(
        upload_to="company_logos/",
        null=True,
        blank=True,
    )

    website = models.URLField(
        null=True,
        blank=True,
    )

    industry = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    timezone = models.CharField(
        max_length=100,
        default="UTC",
    )

    country = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    class Meta:

        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):

        return self.name


class Department(TimeStampedModel):

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="departments",
    )

    name = models.CharField(
        max_length=100,
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )

    description = models.TextField(
        null=True,
        blank=True,
    )

    # =====================================================
    # DEPARTMENT HEAD
    # =====================================================

    head = models.ForeignKey(
        "companies.Membership",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="headed_departments",
    )

    # =====================================================
    # PRIMARY DEPARTMENT CONVERSATION
    # =====================================================

    conversation = models.OneToOneField(
        "chat.Conversation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="managed_department",
    )

    class Meta:

        unique_together = [
            ("company", "name"),
        ]

        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["parent"]),
            models.Index(fields=["head"]),
        ]

    def __str__(self):

        return self.name


class Membership(TimeStampedModel):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    role = models.ForeignKey(
        "rbac.Role",
        on_delete=models.PROTECT,
    )

    # =====================================================
    # PRIMARY DEPARTMENT
    # =====================================================

    department = models.ForeignKey(
        "companies.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="members",
    )

    job_title = models.CharField(
        max_length=150,
        null=True,
        blank=True,
    )

    work_space_email = models.EmailField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
    )

    last_seen = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:

        unique_together = [
            ("user", "company"),
        ]

        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["department"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):

        return (
            f"{self.user} - "
            f"{self.company}"
        )


class CompanyInvite(TimeStampedModel):

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="invites",
    )

    invited_by = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
    )

    email = models.EmailField()

    role = models.ForeignKey(
        "rbac.Role",
        on_delete=models.PROTECT,
    )

    department = models.ForeignKey(
        "companies.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    token_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
    )

    token_hash = models.CharField(
        max_length=255,
    )

    is_used = models.BooleanField(
        default=False,
    )

    expires_at = models.DateTimeField()

    class Meta:

        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["email"]),
            models.Index(fields=["token_id"]),
            models.Index(fields=["expires_at"]),
        ]

    def is_expired(self):

        return timezone.now() > self.expires_at