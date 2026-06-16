from django.db import models

from apps.core.models import (
    TimeStampedModel,
)


class AttendanceRecord(
    TimeStampedModel,
):

    # =====================================================
    # STATUS
    # =====================================================

    class Status(models.TextChoices):

        PRESENT = (
            "present",
            "Present",
        )

        ABSENT = (
            "absent",
            "Absent",
        )

        LATE = (
            "late",
            "Late",
        )

        HALF_DAY = (
            "half_day",
            "Half Day",
        )

        ON_LEAVE = (
            "on_leave",
            "On Leave",
        )

        HOLIDAY = (
            "holiday",
            "Holiday",
        )

        WEEKEND = (
            "weekend",
            "Weekend",
        )

    # =====================================================
    # RELATIONS
    # =====================================================

    membership = models.ForeignKey(
        "companies.Membership",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )

    shift = models.ForeignKey(
        "attendance.Shift",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attendance_records",
    )

    leave_request = models.ForeignKey(
        "attendance.LeaveRequest",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attendance_records",
    )

    # =====================================================
    # DATE
    # =====================================================

    attendance_date = models.DateField()

    # =====================================================
    # CHECK IN / OUT
    # =====================================================

    check_in_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    check_out_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # =====================================================
    # COMPUTED MINUTES
    # =====================================================

    total_work_minutes = models.PositiveIntegerField(
        default=0,
    )

    late_minutes = models.PositiveIntegerField(
        default=0,
    )

    early_exit_minutes = models.PositiveIntegerField(
        default=0,
    )

    overtime_minutes = models.PositiveIntegerField(
        default=0,
    )

    # =====================================================
    # STATUS
    # =====================================================

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.ABSENT,
    )

    is_regularized = models.BooleanField(
        default=False,
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    # =====================================================
    # META
    # =====================================================

    class Meta:

        unique_together = [
            (
                "membership",
                "attendance_date",
            ),
        ]

        ordering = [
            "-attendance_date",
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
                    "attendance_date",
                ]
            ),

            models.Index(
                fields=[
                    "status",
                ]
            ),

            models.Index(
                fields=[
                    "company",
                    "attendance_date",
                ]
            ),
        ]

    def __str__(self):

        return (
            f"{self.membership_id}"
            f" - "
            f"{self.attendance_date}"
            f" - "
            f"{self.status}"
        )
