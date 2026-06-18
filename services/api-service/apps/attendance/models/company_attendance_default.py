from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.companies.models import Company
from apps.attendance.models.company_attendance_method import CompanyAttendanceMethod
from apps.attendance.models.attendance_location import AttendanceLocation
from apps.core.models import TimeStampedModel


class ValidationModeChoices(models.TextChoices):
    PRIMARY = "PRIMARY", _("Primary Method Only")
    ALL = "ALL", _("All Configured Methods Required")
    ANY = "ANY", _("Any Configured Method Allowed")


class CompanyAttendanceDefault(TimeStampedModel):
    """
    Defines fallback attendance methods and location guardrails at the company level.
    Only one active record can exist per company.
    """
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="attendance_default",
        verbose_name=_("Company")
    )
    allowed_methods = models.ManyToManyField(
        CompanyAttendanceMethod,
        related_name="default_configurations",
        verbose_name=_("Allowed Methods")
    )
    validation_mode = models.CharField(
        max_length=15,
        choices=ValidationModeChoices.choices,
        default=ValidationModeChoices.ANY,
        verbose_name=_("Validation Mode")
    )
    allowed_locations = models.ManyToManyField(
        AttendanceLocation,
        blank=True,
        related_name="default_configurations",
        verbose_name=_("Allowed Locations")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active")
    )

    class Meta:
        db_table = "attendance_company_defaults"
        verbose_name = _("Company Attendance Default")
        verbose_name_plural = _("Company Attendance Defaults")

    def __str__(self) -> str:
        return f"{self.company.name} - Default Config"