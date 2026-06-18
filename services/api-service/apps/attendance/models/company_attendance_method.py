from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.companies.models import Company
from apps.companies.models import Membership


class CompanyAttendanceMethod(TimeStampedModel):
    """
    Manages allowed core workspace transaction ingestion interfaces per Tenant context.
    
    This acts as a structural schema switchboard declaring configuration validation paths 
    globally for a Company instance, rather than evaluating explicit employee profile mappings.
    """
    class AttendanceMethodChoices(models.TextChoices):
        WEB = "WEB", _("Web/Mobile Dashboard Portal")
        GPS = "GPS", _("Geofenced Coordinate Boundary")
        FACE = "FACE", _("Biometric Facial Recognition Engine")
        BIOMETRIC = "BIOMETRIC", _("Hardware Fingerprint Terminal")
        MANUAL = "MANUAL", _("Administrative Manual Overwrite")
        QR = "QR", _("QR Code Scanning Framework")  

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="attendance_methods",
        verbose_name=_("Company Workspace Context"),
        db_index=True
    )
    method = models.CharField(
        max_length=30,
        choices=AttendanceMethodChoices.choices,
        verbose_name=_("Ingestion Channel Method Interface"),
        db_index=True
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Operational Verification Flag"),
        help_text=_("Toggles validation availability without executing destructive record purges.")
    )
    created_by = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="configured_attendance_methods",
        verbose_name=_("Audit Trail Instigator")
    )

    class Meta:
        db_table = "attendance_company_methods"
        ordering = ["method"]
        verbose_name = _("Company Attendance Method Configuration")
        verbose_name_plural = _("Company Attendance Method Configurations")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "method"],
                name="unique_company_attendance_method_interface"
            )
        ]

    def __str__(self) -> str:
        return f"{self.company.name} - {self.get_method_display()}"