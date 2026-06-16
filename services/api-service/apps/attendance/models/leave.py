from django.db import models

from apps.core.models import (
    TimeStampedModel,
)


class LeaveType(
    TimeStampedModel,
):

    # =====================================================
    # COMPANY
    # =====================================================

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="leave_types",
    )

    # =====================================================
    # BASIC
    # =====================================================

    name = models.CharField(
        max_length=100,
    )

    code = models.CharField(
        max_length=20,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    # =====================================================
    # CONFIG
    # =====================================================

    annual_quota = models.PositiveIntegerField(
        default=0,
    )

    is_paid = models.BooleanField(
        default=True,
    )

    requires_approval = models.BooleanField(
        default=True,
    )

    allow_half_day = models.BooleanField(
        default=True,
    )

    # =====================================================
    # STATUS
    # =====================================================

    is_active = models.BooleanField(
        default=True,
    )

    # =====================================================
    # META
    # =====================================================

    class Meta:

        unique_together = [
            (
                "company",
                "code",
            ),
        ]

        ordering = [
            "name",
        ]

        indexes = [

            models.Index(
                fields=[
                    "company",
                ]
            ),

            models.Index(
                fields=[
                    "is_active",
                ]
            ),
        ]

    def __str__(self):

        return (
            f"{self.name}"
        )
    






class LeaveRequest(
    TimeStampedModel,
):

    # =====================================================
    # STATUS
    # =====================================================

    class Status(models.TextChoices):

        PENDING = (
            "pending",
            "Pending",
        )

        APPROVED = (
            "approved",
            "Approved",
        )

        REJECTED = (
            "rejected",
            "Rejected",
        )

        CANCELLED = (
            "cancelled",
            "Cancelled",
        )

    # =====================================================
    # EMPLOYEE
    # =====================================================

    membership = models.ForeignKey(
        "companies.Membership",
        on_delete=models.CASCADE,
        related_name="leave_requests",
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="leave_requests",
    )

    leave_type = models.ForeignKey(
        "attendance.LeaveType",
        on_delete=models.PROTECT,
        related_name="leave_requests",
    )

    # =====================================================
    # DATE RANGE
    # =====================================================

    start_date = models.DateField()

    end_date = models.DateField()

    total_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
    )

    # =====================================================
    # HALF DAY
    # =====================================================

    is_half_day = models.BooleanField(
        default=False,
    )

    # =====================================================
    # DETAILS
    # =====================================================

    reason = models.TextField()

    # =====================================================
    # APPROVAL
    # =====================================================

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )

    approved_by = models.ForeignKey(
        "companies.Membership",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_leave_requests",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rejection_reason = models.TextField(
        blank=True,
        default="",
    )

    # =====================================================
    # META
    # =====================================================

    class Meta:

        ordering = [
            "-created_at",
        ]

        indexes = [

            models.Index(
                fields=[
                    "company",
                ]
            ),

            models.Index(
                fields=[
                    "membership",
                ]
            ),

            models.Index(
                fields=[
                    "status",
                ]
            ),

            models.Index(
                fields=[
                    "start_date",
                ]
            ),
        ]

    def __str__(self):

        return (
            f"{self.membership}"
            f" - "
            f"{self.leave_type}"
        )