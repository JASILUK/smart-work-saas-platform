from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.companies.models import Company, Membership
from apps.attendance.models.company_attendance_method import CompanyAttendanceMethod
from apps.attendance.models.attendance_location import AttendanceLocation
from apps.attendance.models.company_attendance_default import ValidationModeChoices


class EmployeeAttendanceOverride(TimeStampedModel):
    """
    Granular employee-specific override configuration. Takes supreme priority 
    over rules and company defaults.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="employee_attendance_overrides",
        verbose_name=_("Company")
    )
    membership = models.OneToOneField(
        Membership,
        on_delete=models.CASCADE,
        related_name="attendance_override",
        verbose_name=_("Employee Membership")
    )
    allowed_methods = models.ManyToManyField(
        CompanyAttendanceMethod,
        related_name="employee_overrides",
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
        related_name="employee_overrides",
        verbose_name=_("Allowed Locations")
    )
    reason = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Reason for Override")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active")
    )

    class Meta:
        db_table = "attendance_employee_overrides"
        verbose_name = _("Employee Attendance Override")
        verbose_name_plural = _("Employee Attendance Overrides")

    def __str__(self) -> str:
        return f"Override: {self.membership.user.username} ({self.company.name})"