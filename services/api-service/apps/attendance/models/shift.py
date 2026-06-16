from django.db import models
from apps.core.models import (
    TimeStampedModel,
)


class Shift(
    TimeStampedModel,
):

    # =====================================================
    # COMPANY
    # =====================================================

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="shifts",
    )

    # =====================================================
    # BASIC
    # =====================================================

    name = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    # =====================================================
    # TIMINGS
    # =====================================================

    start_time = models.TimeField()

    end_time = models.TimeField()

    # =====================================================
    # BREAK
    # =====================================================

    break_duration_minutes = (
        models.PositiveIntegerField(
            default=60,
        )
    )

    # =====================================================
    # NIGHT SHIFT
    # =====================================================

    is_night_shift = (
        models.BooleanField(
            default=False,
        )
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
                "name",
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


class EmployeeShiftAssignment(
    TimeStampedModel,
):

    # =====================================================
    # EMPLOYEE
    # =====================================================

    membership = models.ForeignKey(
        "companies.Membership",
        on_delete=models.CASCADE,
        related_name="shift_assignments",
    )

    # =====================================================
    # SHIFT
    # =====================================================

    shift = models.ForeignKey(
        "attendance.Shift",
        on_delete=models.PROTECT,
        related_name="employee_assignments",
    )

    # =====================================================
    # EFFECTIVE PERIOD
    # =====================================================

    effective_from = models.DateField()

    effective_until = models.DateField(
        null=True,
        blank=True,
    )

    # =====================================================
    # PRIMARY
    # =====================================================

    is_primary = models.BooleanField(
        default=True,
    )

    # =====================================================
    # STATUS
    # =====================================================

    is_active = models.BooleanField(
        default=True,
    )

    # =====================================================
    # ASSIGNED BY
    # =====================================================

    assigned_by = models.ForeignKey(
        "companies.Membership",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_shifts",
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    # =====================================================
    # META
    # =====================================================

    class Meta:

        ordering = [
            "-effective_from",
        ]

        indexes = [

            models.Index(
                fields=[
                    "membership",
                ]
            ),

            models.Index(
                fields=[
                    "shift",
                ]
            ),

            models.Index(
                fields=[
                    "effective_from",
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
            f"{self.membership}"
            f" -> "
            f"{self.shift}"
        )