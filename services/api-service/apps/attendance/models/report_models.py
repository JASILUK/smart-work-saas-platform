# apps/attendance/models/report_models.py
from django.db import models
from apps.core.models import TimeStampedModel
from apps.companies.models import Company, Membership

class HRReportFormat(models.TextChoices):
    CSV = "CSV", "Comma Separated Values"
    EXCEL = "EXCEL", "Microsoft Excel (.xlsx)"
    PDF = "PDF", "Portable Document Format"

class HRReportStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Execution"
    PROCESSING = "PROCESSING", "Processing Data Slices"
    COMPLETED = "COMPLETED", "Completed & Uploaded"
    FAILED = "FAILED", "Execution Failed"

class HRReportScheduleFrequency(models.TextChoices):
    DAILY = "DAILY", "Daily Automated Run"
    WEEKLY = "WEEKLY", "Weekly Automated Run"
    MONTHLY = "MONTHLY", "Monthly Automated Run"
    QUARTERLY = "QUARTERLY", "Quarterly Automated Run"

class HRReportGenerationHistory(TimeStampedModel):
    """
    Maintains append-only logging histories for administrative report generation,
    tracking data boundaries, actor footprints, and artifact links.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="report_histories")
    generated_by = models.ForeignKey(Membership, on_delete=models.SET_NULL, null=True, related_name="generated_reports")
    report_type = models.CharField(max_length=100)
    filters_used = models.JSONField(default=dict)
    export_format = models.CharField(max_length=10, choices=HRReportFormat.choices)
    status = models.CharField(max_length=20, choices=HRReportStatus.choices, default=HRReportStatus.PENDING)
    file_url = models.URLField(max_length=1000, null=True, blank=True)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        db_table = "attendance_report_generation_history"
        ordering = ["-created_at"]

class HRReportAutomationSchedule(TimeStampedModel):
    """
    Stores system configurations for automated report definitions executed by background workers.
    """
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="report_schedules")
    creator = models.ForeignKey(Membership, on_delete=models.SET_NULL, null=True, related_name="created_schedules")
    report_type = models.CharField(max_length=100)
    frequency = models.CharField(max_length=20, choices=HRReportScheduleFrequency.choices)
    filters_template = models.JSONField(default=dict)
    export_format = models.CharField(max_length=10, choices=HRReportFormat.choices, default=HRReportFormat.CSV)
    recipients_emails = models.JSONField(default=list, help_text="Target email notifications list.")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "attendance_report_automation_schedules"
        ordering = ["-created_at"]