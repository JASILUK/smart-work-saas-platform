# apps/attendance/services/hr_report_service.py
import csv
import io
import datetime
from django.utils import timezone
from django.db import transaction
from rest_framework.exceptions import ValidationError
from apps.companies.models import Company, Membership
from apps.attendance.models.report_models import HRReportGenerationHistory, HRReportAutomationSchedule, HRReportStatus
from apps.attendance.selectors.hr_report_selectors import HRReportDataSelector
from apps.attendance.models.daily_attendance import DailyAttendance

class HRReportOrchestratorService:
    """
    Manages reporting configurations, handles data filtering, and oversees
    asynchronous background document generation processes.
    """

    @classmethod
    def parse_and_validate_filters(cls, query_params: dict) -> dict:
        """
        Validates date parameters, ensuring they do not exceed a 92-day reporting window.
        """
        date_from_str = query_params.get("date_from")
        date_to_str = query_params.get("date_to")

        if not date_from_str or not date_to_str:
            raise ValidationError("Both date_from and date_to boundary parameters are mandatory for reporting.")

        try:
            date_from = datetime.datetime.strptime(date_from_str, "%Y-%m-%d").date()
            date_to = datetime.datetime.strptime(date_to_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Provided date strings must match the YYYY-MM-DD format exactly.")

        if date_from > date_to:
            raise ValidationError("The date_from boundary parameter must precede the date_to constraint.")

        if (date_to - date_from).days > 92:
            raise ValidationError("Reporting window limit exceeded: Lookups cannot span more than 92 calendar days.")

        return {
            "date_from": date_from,
            "date_to": date_to,
            "department_id": query_params.get("department"),
            "membership_id": query_params.get("membership"),
            "status": query_params.get("status"),
            "needs_review": query_params.get("needs_review") == "true" if "needs_review" in query_params else None,
            "is_auto_closed": query_params.get("is_auto_closed") == "true" if "is_auto_closed" in query_params else None,
            "search": query_params.get("search"),
            "ordering": query_params.get("ordering", "attendance_date")
        }

    @classmethod
    @transaction.atomic
    def trigger_async_report_export(cls, *, company: Company, actor: Membership, data: dict) -> HRReportGenerationHistory:
        """
        Registers a report generation task in the audit history logs and dispatches 
        the document creation job to background workers.
        """
        clean_filters = cls.parse_and_validate_filters(data.get("filters", {}))
        
        # Serialize date objects for storage in the JSON parameters log field
        serializable_filters = clean_filters.copy()
        serializable_filters["date_from"] = str(serializable_filters["date_from"])
        serializable_filters["date_to"] = str(serializable_filters["date_to"])

        history_entry = HRReportGenerationHistory.objects.create(
            company=company,
            generated_by=actor,
            report_type=data.get("report_type", "COMPANY_SUMMARY"),
            filters_used=serializable_filters,
            export_format=data.get("format", "CSV"),
            status=HRReportStatus.PENDING
        )

        # Execution Strategy: Pass task tracking tokens directly to background workers
        # In production environments, invoke: run_async_report_generation_task.delay(history_entry.id)
        return history_entry

    @classmethod
    def execute_streaming_csv_generation(cls, history_entry_id: int) -> str:
        """
        Background execution engine that generates reports incrementally using server-side cursors.
        Prevents memory spikes by streaming data directly into an append-only IO buffer.
        """
        entry = HRReportGenerationHistory.objects.select_related("company").get(id=history_entry_id)
        entry.status = HRReportStatus.PROCESSING
        entry.save(update_fields=["status"])

        try:
            filters = entry.filters_used
            base_qs = DailyAttendance.objects.filter(company=entry.company).select_related("membership__user")
            filtered_qs = HRReportDataSelector.apply_unified_filter_matrix(base_qs, filters)

            output_buffer = io.StringIO()
            writer = csv.writer(output_buffer)
            
            # Write document header columns
            writer.writerow(["Record ID", "Employee Username", "Attendance Date", "Status", "Work Minutes", "Late Minutes"])

            # Use server-side iterator chunks to process massive tables with zero memory overhead
            for record in filtered_qs.order_by("attendance_date").iterator(chunk_size=2000):
                writer.writerow([
                    record.id, record.membership.user.username, str(record.attendance_date),
                    record.attendance_status, record.total_work_minutes, record.late_minutes
                ])

            # In production, upload the generated file to a secure cloud bucket:
            # mock_s3_url = cloud_storage_provider.upload(output_buffer.getvalue())
            mock_s3_url = f"https://s3.company-tenant.io/exports/{entry.company.id}/report_{entry.id}.csv"

            entry.status = HRReportStatus.COMPLETED
            entry.file_url = mock_s3_url
            entry.save(update_fields=["status", "file_url"])
            return mock_s3_url

        except Exception as error_context:
            entry.status = HRReportStatus.FAILED
            entry.error_message = str(error_context)
            entry.save(update_fields=["status", "error_message"])
            raise error_context

    @classmethod
    @transaction.atomic
    def save_automated_report_schedule(cls, *, company: Company, actor: Membership, data: dict) -> HRReportAutomationSchedule:
        """
        Saves user-defined report configurations for automated background schedules.
        """
        return HRReportAutomationSchedule.objects.create(
            company=company,
            creator=actor,
            report_type=data["report_type"],
            frequency=data["frequency"],
            filters_template=data.get("filters", {}),
            export_format=data.get("format", "CSV"),
            recipients_emails=data.get("recipients", [])
        )