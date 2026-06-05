from django.db import models

from apps.core.models import TimeStampedModel


class Reminder(TimeStampedModel):

    # =====================================================
    # TARGET TYPE
    # =====================================================

    class TargetType(models.TextChoices):

        MEETING = "meeting", "Meeting"

        PAYROLL = "payroll", "Payroll"

        ATTENDANCE = "attendance", "Attendance"

        PROJECT = "project", "Project"

        TASK = "task", "Task"

        INVOICE = "invoice", "Invoice"

        SUBSCRIPTION = "subscription", "Subscription"

    # =====================================================
    # STATUS
    # =====================================================

    class Status(models.TextChoices):

        PENDING = "pending", "Pending"

        PROCESSING = "processing", "Processing"

        SENT = "sent", "Sent"

        FAILED = "failed", "Failed"

        CANCELLED = "cancelled", "Cancelled"

    # =====================================================
    # RELATIONS
    # =====================================================

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="reminders",
    )

    recipient_membership = models.ForeignKey(
        "companies.Membership",
        on_delete=models.CASCADE,
        related_name="reminders",
    )

    # =====================================================
    # TARGET
    # =====================================================

    target_type = models.CharField(
        max_length=50,
        choices=TargetType.choices,
    )

    target_id = models.PositiveBigIntegerField()

    # =====================================================
    # SCHEDULING
    # =====================================================

    remind_at = models.DateTimeField()

    minutes_before = models.PositiveIntegerField(
        default=0,
    )

    # =====================================================
    # DELIVERY
    # =====================================================

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    failure_reason = models.TextField(
        blank=True,
        default="",
    )

    # =====================================================
    # EXTRA
    # =====================================================

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:

        indexes = [

            models.Index(
                fields=["status"],
            ),

            models.Index(
                fields=["remind_at"],
            ),

            models.Index(
                fields=[
                    "target_type",
                    "target_id",
                ],
            ),

            models.Index(
                fields=[
                    "recipient_membership",
                ],
            ),

            models.Index(
                fields=[
                    "status",
                    "remind_at",
                ],
            ),
        ]

    def __str__(self):

        return (
            f"{self.target_type}"
            f" - "
            f"{self.recipient_membership_id}"
            f" - "
            f"{self.remind_at}"
        )