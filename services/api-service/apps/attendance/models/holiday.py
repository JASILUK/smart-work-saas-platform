from django.db import models

from apps.core.models import (
    TimeStampedModel,
)


class Holiday(
    TimeStampedModel,
):

    # =====================================================
    # TYPE
    # =====================================================

    class HolidayType(models.TextChoices):

        NATIONAL = (
            "national",
            "National",
        )

        STATE = (
            "state",
            "State",
        )

        COMPANY = (
            "company",
            "Company",
        )

        OPTIONAL = (
            "optional",
            "Optional",
        )

    # =====================================================
    # COMPANY
    # =====================================================

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="holidays",
    )

    # =====================================================
    # BASIC
    # =====================================================

    name = models.CharField(
        max_length=255,
    )

    holiday_type = models.CharField(
        max_length=30,
        choices=HolidayType.choices,
        default=HolidayType.COMPANY,
    )

    holiday_date = models.DateField()

    description = models.TextField(
        blank=True,
        default="",
    )

    # =====================================================
    # CONFIG
    # =====================================================

    is_paid = models.BooleanField(
        default=True,
    )

    is_half_day = models.BooleanField(
        default=False,
    )

    # =====================================================
    # EXTERNAL SYNC
    # =====================================================

    external_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    provider = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # =====================================================
    # META
    # =====================================================

    class Meta:

        unique_together = [
            (
                "company",
                "holiday_date",
                "name",
            ),
        ]

        ordering = [
            "holiday_date",
        ]

        indexes = [

            models.Index(
                fields=[
                    "company",
                ]
            ),

            models.Index(
                fields=[
                    "holiday_date",
                ]
            ),

            models.Index(
                fields=[
                    "holiday_type",
                ]
            ),
        ]

    def __str__(self):

        return (
            f"{self.name}"
            f" ({self.holiday_date})"
        )