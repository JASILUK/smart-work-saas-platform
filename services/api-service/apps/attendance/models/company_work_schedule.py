from django.db import models

from apps.core.models import (
    TimeStampedModel,
)


class CompanyWorkSchedule(
    TimeStampedModel,
):

    # =====================================================
    # COMPANY
    # =====================================================

    company = models.OneToOneField(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="work_schedule",
    )

    # =====================================================
    # WORKING DAYS
    # =====================================================

    working_days = models.JSONField(
        default=list,
    )

    weekend_days = models.JSONField(
        default=list,
    )

    # =====================================================
    # DEFAULT HOURS
    # =====================================================

    work_start_time = models.TimeField()

    work_end_time = models.TimeField()

    break_minutes = models.PositiveIntegerField(
        default=60,
    )

    default_shift = models.ForeignKey(
        "attendance.Shift",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="default_work_schedules",
    )

    # =====================================================
    # REGION
    # =====================================================

    timezone = models.CharField(
        max_length=100,
    )

    country = models.CharField(
        max_length=100,
    )

    state = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # =====================================================
    # HOLIDAY SETTINGS
    # =====================================================

    holiday_sync_enabled = models.BooleanField(
        default=False,
    )

    holiday_provider = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # =====================================================
    # STATUS
    # =====================================================

    is_active = models.BooleanField(
        default=True,
    )

    # =====================================================
    # INDEXES
    # =====================================================

    class Meta:

        indexes = [

            models.Index(
                fields=["company"],
            ),

            models.Index(
                fields=["country"],
            ),

            models.Index(
                fields=["default_shift"],
            ),

            models.Index(
                fields=["is_active"],
            ),
        ]

    def __str__(self):

        return (
            f"{self.company.name}"
            f" Work Schedule"
        )