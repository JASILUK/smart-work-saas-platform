from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.companies.models import Company, Department, Membership
from apps.attendance.models.company_attendance_method import CompanyAttendanceMethod
from apps.attendance.models.attendance_location import AttendanceLocation
from apps.attendance.models.company_attendance_default import ValidationModeChoices


class ScopeTypeChoices(models.TextChoices):
    WORK_MODE = "WORK_MODE", _("Work Mode Scope")
    DEPARTMENT = "DEPARTMENT", _("Department Scope")


class AttendanceAccessRule(TimeStampedModel):
    """
    Defines policy overrides for groups of employees based on department or work mode.
    Evaluated by lower priority values taking precedence.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="attendance_access_rules",
        verbose_name=_("Company")
    )
    name = models.CharField(
        max_length=150,
        verbose_name=_("Rule Name")
    )
    scope_type = models.CharField(
        max_length=20,
        choices=ScopeTypeChoices.choices,
        verbose_name=_("Scope Type")
    )
    work_mode = models.CharField(
        max_length=30,
        choices=Membership.WorkMode.choices,
        null=True,
        blank=True,
        verbose_name=_("Target Work Mode")
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attendance_access_rules",
        verbose_name=_("Target Department")
    )
    allowed_methods = models.ManyToManyField(
        CompanyAttendanceMethod,
        related_name="access_rules",
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
        related_name="access_rules",
        verbose_name=_("Allowed Locations")
    )
    priority = models.PositiveIntegerField(
        default=10,
        verbose_name=_("Evaluation Priority")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active")
    )

    class Meta:
        db_table = "attendance_access_rules"
        ordering = ["priority", "name"]
        verbose_name = _("Attendance Access Rule")
        verbose_name_plural = _("Attendance Access Rules")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "scope_type", "work_mode", "department"],
                condition=Q(is_active=True),
                name="unique_active_rule_combination"
            )
        ]

    def __str__(self) -> str:
        return f"{self.company.name} - Rule: {self.name} (P:{self.priority})"