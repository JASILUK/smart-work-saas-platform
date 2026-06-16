from django.db import models

from apps.core.models import (
    TimeStampedModel,
)


class AttendancePolicy(
    TimeStampedModel,
):

    # =====================================================
    # COMPANY
    # =====================================================

    company = models.OneToOneField(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="attendance_policy",
    )

    # =====================================================
    # WORK REQUIREMENTS
    # =====================================================

    required_work_minutes = models.PositiveIntegerField(
        default=480,
    )

    half_day_below_minutes = models.PositiveIntegerField(
        default=240,
    )

    # =====================================================
    # LATE ARRIVAL
    # =====================================================

    late_after_minutes = models.PositiveIntegerField(
        default=10,
    )

    # =====================================================
    # EARLY EXIT
    # =====================================================

    early_exit_before_minutes = models.PositiveIntegerField(
        default=30,
    )

    # =====================================================
    # OVERTIME
    # =====================================================

    overtime_enabled = models.BooleanField(
        default=False,
    )

    overtime_after_minutes = models.PositiveIntegerField(
        default=480,
    )

    # =====================================================
    # ABSENT RULES
    # =====================================================

    auto_absent_if_no_checkin = models.BooleanField(
        default=True,
    )

    # =====================================================
    # WEEKEND WORK
    # =====================================================

    count_weekend_as_overtime = models.BooleanField(
        default=False,
    )

    # =====================================================
    # ATTENDANCE CORRECTION
    # =====================================================

    attendance_regularization_enabled = models.BooleanField(
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

        indexes = [

            models.Index(
                fields=[
                    "is_active",
                ]
            ),
        ]

    def __str__(self):

        return (
            f"{self.company.name} "
            f"Attendance Policy"
        )