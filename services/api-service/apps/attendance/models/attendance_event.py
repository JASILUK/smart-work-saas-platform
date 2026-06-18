from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.companies.models import Company, Membership
from apps.attendance.models.attendance_location import AttendanceLocation
from apps.attendance.models.face_enrollment import FaceEnrollment
from apps.attendance.models.biometric_log import BiometricLog


class AttendanceEventTypes(models.TextChoices):
    CHECK_IN = "CHECK_IN", _("Clock In Event")
    CHECK_OUT = "CHECK_OUT", _("Clock Out Event")
    BREAK_OUT = "BREAK_OUT", _("Begin Break Intermission")
    BREAK_IN = "BREAK_IN", _("Return From Break Intermission")


class AttendanceMethodChoices(models.TextChoices):
    GPS_FACE = "GPS_FACE", _("Combined Geofence & Facial Matching")
    GPS_ONLY = "GPS_ONLY", _("Geofence Verification Only")
    FACE_ONLY = "FACE_ONLY", _("Facial Identification Portal Only")
    BIOMETRIC = "BIOMETRIC", _("Hardware Fingerprint Terminal Interface")
    MANUAL = "MANUAL", _("HR Administrative Overwrite Adjustment")


class AttendanceEvent(TimeStampedModel):
    """
    Maintains an immutable auditing trail tracking individual punch interactions.
    Serves as the primary transaction source layer feeding downstream calculations.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="attendance_events",
        verbose_name=_("Company Context Scope Target"),
        db_index=True
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name="attendance_events",
        verbose_name=_("Employee Profile Target"),
        db_index=True
    )
    event_type = models.CharField(
        max_length=20,
        choices=AttendanceEventTypes.choices,
        verbose_name=_("Workflow Event Action Action Type")
    )
    attendance_method = models.CharField(
        max_length=20,
        choices=AttendanceMethodChoices.choices,
        verbose_name=_("Verification Pathway Channel Used")
    )
    event_time = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Timezone Aware Punch Time Timestamp UTC")
    )
    location = models.ForeignKey(
        AttendanceLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_events",
        verbose_name=_("Matched Geofence Perimeter Point Location")
    )
    face_enrollment = models.ForeignKey(
        FaceEnrollment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_events",
        verbose_name=_("Matched Biometric Face Enrollment Signature")
    )
    biometric_log = models.ForeignKey(
        BiometricLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_events",
        verbose_name=_("Linked Streaming Raw Hardware Log Sync Record")
    )
    verification_payload = models.JSONField(
        default=dict,
        verbose_name=_("Ingestion Metadata Evidence Payload Snapshot File")
    )
    notes = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Administrative Narrative Notes Text")
    )
    created_by = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="instigated_attendance_events",
        verbose_name=_("Action Trail Instigator Profile Context")
    )
    is_system_generated = models.BooleanField(
        default=False,
        verbose_name=_("Automated Machine Event Trigger Flag")
    )

    class Meta:
        db_table = "attendance_events"
        ordering = ["-event_time"]
        verbose_name = "Attendance Workflow Action Event"
        verbose_name_plural = "Attendance Workflow Action Events"
        
        indexes = [
            models.Index(fields=["company", "membership", "event_time"], name="att_evt_member_time_idx"),
            models.Index(fields=["company", "event_time"], name="att_evt_company_time_idx"),
            models.Index(fields=["company", "event_type"], name="att_evt_type_idx"),
            models.Index(fields=["company", "attendance_method"], name="att_evt_method_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.membership.user.username} - {self.event_type} ({self.event_time})"