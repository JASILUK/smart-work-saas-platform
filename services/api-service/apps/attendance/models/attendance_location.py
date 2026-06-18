from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.companies.models import Company, Membership


class AttendanceLocation(TimeStampedModel):
    """
    Manages physical geo-fenced perimeters (GPS ranges) configured per Company workspace.
    
    Tied directly into verification routines. Records are never physically deleted 
    to preserve downstream transaction integrity on historical punch-in summaries.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="attendance_locations",
        verbose_name=_("Company Workspace Context"),
        db_index=True
    )
    name = models.CharField(
        max_length=150,
        verbose_name=_("Location Label Name")
    )
    address = models.TextField(
        default="",
        blank=True,
        verbose_name=_("Human Readable Address Description")
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name=_("Target Latitude Coordinate")
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        verbose_name=_("Target Longitude Coordinate")
    )
    radius_meters = models.PositiveIntegerField(
        default=150,
        verbose_name=_("Geofence Radius Threshold Bounds")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Operational Verification Flag"),
        help_text=_("Determines if employees are evaluated against this boundary.")
    )
    created_by = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_attendance_locations",
        verbose_name=_("Audit Trail Instigator")
    )

    class Meta:
        db_table = "attendance_locations"
        ordering = ["name"]
        verbose_name = _("Attendance Location Perimeter")
        verbose_name_plural = _("Attendance Location Perimeters")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                condition=Q(is_active=True),
                name="unique_active_location_name_per_company"
            )
        ]

    def __str__(self) -> str:
        return f"{self.company.name} - {self.name} ({self.radius_meters}m)"