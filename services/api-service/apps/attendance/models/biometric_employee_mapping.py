from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.companies.models import Company, Membership
from apps.attendance.models.biometric_device import BiometricDevice


class BiometricEmployeeMapping(TimeStampedModel):
    """
    Maintains user mapping profiles connecting internal multi-tenant platform Membership references 
    to specific terminal identification tracking IDs populated on local device partitions.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="biometric_employee_mappings",
        verbose_name=_("Company Context Dashboard Scope"),
        db_index=True
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name="biometric_mappings",
        verbose_name=_("Employee Profile Context Reference")
    )
    device = models.ForeignKey(
        BiometricDevice,
        on_delete=models.CASCADE,
        related_name="employee_mappings",
        verbose_name=_("Assigned Biometric Device Terminal Target")
    )
    device_user_id = models.CharField(
        max_length=100,
        verbose_name=_("Hardware Internal Device User ID Index")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active Processing State Flag"),
        help_text=_("Disabling ignores streaming clock log hashes associated with this pairing string context.")
    )
    enrolled_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("System Registration Ingestion Timestamp")
    )
    created_by = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_biometric_mappings",
        verbose_name=_("Audit Trail Instigator Reference Context")
    )

    class Meta:
        db_table = "attendance_biometric_employee_mappings"
        ordering = ["membership"]
        verbose_name = "Biometric Employee Identity Mapping"
        verbose_name_plural = "Biometric Employee Identity Mappings"
        
        constraints = [
            models.UniqueConstraint(
                fields=["company", "device", "device_user_id"],
                name="unique_device_user_identity_per_company"
            ),
            models.UniqueConstraint(
                fields=["company", "membership", "device"],
                name="unique_employee_device_pairing_per_company"
            ),
        ]
        indexes = [
            models.Index(fields=["company", "membership"], name="biom_map_member_idx"),
            models.Index(fields=["company", "device"], name="biom_map_device_idx"),
            models.Index(fields=["company", "is_active"], name="biom_map_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.membership.user.username} ──► ID: {self.device_user_id} ({self.device.name})"