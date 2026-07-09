# apps/attendance/services/hr_review_service.py
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance
from apps.attendance.models.employee_attendance_override import EmployeeAttendanceOverride

class HRReviewService:
    """
    Unyielding execution orchestrator driving state clearance on employee tracking summaries.
    Enforces atomic write consistency and creates immutable audit log entries.
    """

    @classmethod
    def _get_locked_attendance_record(cls, company: Company, record_id: int) -> DailyAttendance:
        """
        Pessimistically locks the target row within the active tenant's context boundary.
        """
        record = DailyAttendance.objects.filter(id=record_id, company=company).select_for_update().first()
        if not record:
            raise NotFound("The requested attendance record anomaly was not found in this company workspace.")
        return record

    @classmethod
    def _write_audit_log(cls, *, company: Company, actor: Membership, record: DailyAttendance, reason: str, field_meta: str) -> None:
        """
        Appends entries into the system's shared corporate modifications sub-ledger.
        """
        EmployeeAttendanceOverride.objects.create(
            company=company,
            employee=record.membership,
            override_by=actor,
            field_name=field_meta,
            old_value="needs_review=True",
            new_value="needs_review=False",
            reason=reason
        )

    @classmethod
    @transaction.atomic
    def resolve_review(cls, *, company: Company, actor: Membership, record_id: int, justification: str) -> DailyAttendance:
        """
        Resolves an outstanding tracking exception. 
        Clears evaluation flags without altering raw timeline configurations.
        """
        record = cls._get_locked_attendance_record(company, record_id)

        if not record.needs_review:
            raise ValidationError("Operational anomaly mismatch: This record summary does not require an active review.")

        if record.finalized_at:
            raise ValidationError("Payroll boundary constraint: This record sheet has already been finalized.")

        # Clear exception indicators
        record.needs_review = False
        record.review_reason = ""
        record.updated_at = timezone.now()
        record.save(update_fields=["needs_review", "review_reason", "updated_at"])

        # Write audit logs entries
        cls._write_audit_log(
            company=company,
            actor=actor,
            record=record,
            reason=justification,
            field_meta="HR_REVIEW_RESOLUTION"
        )

        return record

    @classmethod
    @transaction.atomic
    def append_note(cls, *, company: Company, actor: Membership, record_id: int, note_text: str) -> DailyAttendance:
        """
        Appends internal compliance investigation notes directly to the unalterable audit log infrastructure.
        """
        record = cls._get_locked_attendance_record(company, record_id)

        if not record.needs_review:
            raise ValidationError("Operational variance error: Cannot append investigation notes to resolved entries.")

        # Ingest note data directly into the shared audit ledger system without changing calculation properties
        cls._write_audit_log(
            company=company,
            actor=actor,
            record=record,
            reason=note_text,
            field_meta="HR_INVESTIGATION_NOTE"
        )
        
        record.updated_at = timezone.now()
        record.save(update_fields=["updated_at"])
        return record