import zoneinfo
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.companies.models import Company


class BiometricDeviceBrand(models.TextChoices):
    ZKTECO = "ZKTECO", _("ZKTEco")
    ESSL = "ESSL", _("eSSL")
    SUPREMA = "SUPREMA", _("Suprema")
    HIKVISION = "HIKVISION", _("Hikvision")
    MATRIX = "MATRIX", _("Matrix")
    OTHER = "OTHER", _("Other/Generic Vendor")


class BiometricSyncMode(models.TextChoices):
    PULL = "PULL", _("HRMS Fetches Logs (Scheduled Pull)")
    PUSH = "PUSH", _("Device Pushes Logs (Real-time HTTP/Cloud)")
    MANUAL = "MANUAL", _("Administrative Manual File Import")


class BiometricDevice(TimeStampedModel):
    """
    Represents a physical or network-reachable biometric logging hardware terminal 
    deployed within a company workspace.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="biometric_devices",
        verbose_name=_("Company Context"),
        db_index=True
    )
    name = models.CharField(
        max_length=150,
        verbose_name=_("Device Display Name")
    )
    device_code = models.CharField(
        max_length=50,
        verbose_name=_("Human Readable Device Identifier")
    )
    brand = models.CharField(
        max_length=20,
        choices=BiometricDeviceBrand.choices,
        default=BiometricDeviceBrand.OTHER,
        verbose_name=_("Hardware Vendor Brand")
    )
    model_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=_("Vendor Model Specification Number")
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("Network IP Address"),
        help_text=_("Required for hardware deployed under direct PULL-based synchronization frameworks.")
    )
    port = models.IntegerField(
        default=4370,
        verbose_name=_("Communication Network Port")
    )
    serial_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_("Hardware Factory Serial Number")
    )
    timezone = models.CharField(
        max_length=100,
        default="Asia/Kolkata",
        verbose_name=_("Device Local Operating Timezone")
    )
    sync_mode = models.CharField(
        max_length=15,
        choices=BiometricSyncMode.choices,
        default=BiometricSyncMode.MANUAL,
        verbose_name=_("Synchronization Architecture Interface Mode")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Operational Tracking Status Flag"),
        help_text=_("Deactivating blocks background log synchronization while maintaining transaction history lines.")
    )
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Successful Sync Timeline Mark")
    )

    class Meta:
        db_table = "attendance_biometric_devices"
        ordering = ["name"]
        verbose_name = "Biometric Device Terminal"
        verbose_name_plural = "Biometric Device Terminals"
        
        constraints = [
            models.UniqueConstraint(
                fields=["company", "device_code"],
                name="unique_device_code_per_company"
            ),
            models.UniqueConstraint(
                fields=["company", "serial_number"],
                condition=models.Q(serial_number__isnull=False),
                name="unique_active_serial_number_per_company"
            ),
        ]
        indexes = [
            models.Index(fields=["company", "is_active"], name="biom_dev_active_idx"),
            models.Index(fields=["company", "sync_mode"], name="biom_dev_sync_mode_idx"),
            models.Index(fields=["company", "brand"], name="biom_dev_brand_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.device_code}) - {self.company.name}"