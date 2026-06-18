import uuid
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.companies.models import Company, Membership
from apps.attendance.models.biometric_device import BiometricDevice


class BiometricEventChoices(models.TextChoices):
    CHECK_IN = "CHECK_IN", _("Clock In Punch Event")
    CHECK_OUT = "CHECK_OUT", _("Clock Out Punch Event")
    BREAK_OUT = "BREAK_OUT", _("Break Out Intermission Event")
    BREAK_IN = "BREAK_IN", _("Break In Return Event")
    UNKNOWN = "UNKNOWN", _("Unclassified Ingestion Pulse")


class ProcessingStatusChoices(models.TextChoices):
    PENDING = "PENDING", _("Awaiting Calculation Engine Evaluation")
    PROCESSED = "PROCESSED", _("Successfully Parsed Into Dynamic Shift Records")
    FAILED = "FAILED", _("Processing Exception Blocked Execution")
    IGNORED = "IGNORED", _("De-duplicated/Omitted from Calculations")


class BiometricLog(TimeStampedModel):
    """
    Acts as an immutable, auditing-compliant transactional timeline logging 
    raw device data signals before processing business rules.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="biometric_logs",
        verbose_name=_("Company Context Scope Target"),
        db_index=True
    )
    device = models.ForeignKey(
        BiometricDevice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="biometric_logs",
        verbose_name=_("Originating Device Configuration")
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="biometric_logs",
        verbose_name=_("Resolved Employee Identity Profile Map Context")
    )
    device_user_id = models.CharField(
        max_length=100,
        verbose_name=_("Hardware Internal Device Identity Pointer Tag")
    )
    event_type = models.CharField(
        max_length=20,
        choices=BiometricEventChoices.choices,
        default=BiometricEventChoices.UNKNOWN,
        verbose_name=_("Calculated Raw Event Mode Action")
    )
    punch_time = models.DateTimeField(
        verbose_name=_("Timezone Aware Ingestion UTC Timestamp Execution")
    )
    device_log_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("Hardware Unique Vendor Transaction Instance ID")
    )
    source = models.CharField(
        max_length=15,
        choices=models.TextChoices("Source", "PULL PUSH MANUAL").choices,
        verbose_name=_("Ingestion Transmission Vector Route")
    )
    raw_payload = models.JSONField(
        default=dict,
        verbose_name=_("Immutable Context Metadata Footprint Payload Snapshot")
    )
    sync_batch_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("Execution Orchestration Pipeline Sync Batch Index Identifier")
    )
    processing_status = models.CharField(
        max_length=15,
        choices=ProcessingStatusChoices.choices,
        default=ProcessingStatusChoices.PENDING,
        verbose_name=_("State Status Management Engine Node")
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Consumption Timestamp Execution Mark")
    )
    failure_reason = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Processing Failure Error Diagnostic Log Out")
    )

    class Meta:
        db_table = "attendance_biometric_logs"
        ordering = ["-punch_time"]
        verbose_name = "Biometric Raw Device Punch Log"
        verbose_name_plural = "Biometric Raw Device Punch Logs"
        
        constraints = [
            models.UniqueConstraint(
                fields=["company", "device", "device_log_id"],
                condition=models.Q(device_log_id__isnull=False) & models.Q(device__isnull=False),
                name="unique_vendor_log_transaction_per_device_perimeter"
            ),
        ]
        indexes = [
            models.Index(fields=["company", "punch_time"], name="biom_log_company_time_idx"),
            models.Index(fields=["company", "processing_status"], name="biom_log_status_idx"),
            models.Index(fields=["company", "device"], name="biom_log_device_idx"),
            models.Index(fields=["company", "membership"], name="biom_log_member_idx"),
            models.Index(fields=["company", "source"], name="biom_log_source_idx"),
        ]
        
    def __str__(self) -> str:
        return f"Log #{self.id} ──► Employee Profile Map Context ID: {self.device_user_id} ({self.punch_time})"