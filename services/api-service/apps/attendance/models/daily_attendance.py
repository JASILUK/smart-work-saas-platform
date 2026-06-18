from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.companies.models import Company, Membership
from apps.attendance.models.attendance_access_rule import AttendanceAccessRule


class DailyAttendanceStatus(models.TextChoices):
    PRESENT = "PRESENT", _("Present")
    ABSENT = "ABSENT", _("Absent")
    HALF_DAY = "HALF_DAY", _("Half Day")
    LEAVE = "LEAVE", _("On Approved Leave")
    HOLIDAY = "HOLIDAY", _("Company Observed Holiday")
    WEEKEND = "WEEKEND", _("Scheduled Weekend Rest Day")
    INCOMPLETE = "INCOMPLETE", _("Incomplete Tracking Sequence")
    REVIEW_REQUIRED = "REVIEW_REQUIRED", _("HR Administrative Review Required")


class DailyAttendanceInflowSource(models.TextChoices):
    ENGINE = "ENGINE", _("Automated Processing Pipeline Engine")
    MANUAL = "MANUAL", _("Explicit HR Administrator Overwrite")
    REPROCESSED = "REPROCESSED", _("Historical Recalculation Synchronization")


class DailyAttendance(TimeStampedModel):
    """
    Maintains production-frozen daily evaluation metrics aggregated per employee workspace day.
    Guarantees absolute payroll-readiness through schema immutable json snapshot variables.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="daily_attendance_records",
        verbose_name=_("Company Context Scope")
    )
    membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name="daily_attendance_records",
        verbose_name=_("Employee Profile Reference Context")
    )
    attendance_date = models.DateField(
        verbose_name=_("Operational Tracking Target Date"),
        db_index=True
    )
    
    # Context snapshots
    schedule_snapshot = models.JSONField(
        default=dict,
        verbose_name=_("Frozen Operating Schedule Specifications"),
        help_text=_("Captures work hours and shift structures active on tracking runtime context.")
    )
    policy_snapshot = models.JSONField(
        default=dict,
        verbose_name=_("Frozen Administrative Governance Rules"),
        help_text=_("Captures thresholds for lateness grace scales, half-day cuts, and overtime activation.")
    )
    
    # Time-Tracking Metrics Boundaries
    first_check_in_at = models.DateTimeField(null=True, blank=True, verbose_name=_("First Clock In Log"))
    last_check_out_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Clock Out Log"))
    
    total_work_minutes = models.PositiveIntegerField(default=0, verbose_name=_("Net Active Work Minutes"))
    total_break_minutes = models.PositiveIntegerField(default=0, verbose_name=_("Net Active Break Minutes"))
    required_work_minutes = models.PositiveIntegerField(default=0, verbose_name=_("Mandatory Target Output Minutes"))
    overtime_minutes = models.PositiveIntegerField(default=0, verbose_name=_("Validated Overtime Minutes"))
    late_minutes = models.PositiveIntegerField(default=0, verbose_name=_("Lateness Accumulation Minutes"))
    early_exit_minutes = models.PositiveIntegerField(default=0, verbose_name=_("Early Exit Departure Variance Minutes"))
    
    # State Status Indicators Flag Array
    attendance_status = models.CharField(
        max_length=20,
        choices=DailyAttendanceStatus.choices,
        default=DailyAttendanceStatus.ABSENT,
        verbose_name=_("Daily Synthesis Calculation Status")
    )
    is_present = models.BooleanField(default=False)
    is_half_day = models.BooleanField(default=False)
    is_absent = models.BooleanField(default=True)
    is_late = models.BooleanField(default=False)
    is_early_exit = models.BooleanField(default=False)
    is_holiday = models.BooleanField(default=False)
    is_weekend = models.BooleanField(default=False)
    is_leave = models.BooleanField(default=False)
    
    # Exception Control Tracking Columns
    is_auto_closed = models.BooleanField(default=False, verbose_name=_("Machine Automated Closure Flag"))
    auto_close_reason = models.CharField(max_length=255, blank=True, default="", verbose_name=_("Auto-checkout Narrative Summary"))
    needs_review = models.BooleanField(default=False, verbose_name=_("HR Attention Exception Alert Flag"))
    review_reason = models.TextField(blank=True, default="", verbose_name=_("HR Evaluation Diagnostic Log Out"))
    
    # Immutable Accounting Audits Tracks Block
    finalized_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Payroll Freezing Timestamp"))
    finalized_by = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finalized_daily_attendance_sheets",
        verbose_name=_("Freezing Auditor Profile Context")
    )
    source = models.CharField(
        max_length=20,
        choices=DailyAttendanceInflowSource.choices,
        default=DailyAttendanceInflowSource.ENGINE,
        verbose_name=_("Processing Operation Flow Provenance Origin")
    )

    class Meta:
        db_table = "attendance_daily_summary_ledger"
        ordering = ["-attendance_date", "membership"]
        verbose_name = "Daily Attendance Ledger Summary Record"
        verbose_name_plural = "Daily Attendance Ledger Summary Records"
        
        # Unique constraints remain here
        constraints = [
            models.UniqueConstraint(
                fields=["company", "membership", "attendance_date"],
                name="unique_daily_attendance_summary_per_employee_date"
            ),
        ]
        
        # Fast query indexes are cleanly designated here with descriptive names
        indexes = [
            models.Index(fields=["company", "attendance_date"], name="daily_att_company_date_idx"),
            models.Index(fields=["company", "membership"], name="daily_att_company_member_idx"),
            models.Index(fields=["company", "attendance_status"], name="daily_att_company_status_idx"),
            models.Index(fields=["company", "finalized_at"], name="daily_att_finalized_idx"),
            models.Index(fields=["company", "attendance_date", "attendance_status"], name="daily_att_date_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.membership.user.username} ──► {self.attendance_date} ({self.attendance_status})"