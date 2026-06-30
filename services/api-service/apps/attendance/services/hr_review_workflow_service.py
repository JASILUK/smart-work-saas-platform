# apps/attendance/services/hr_review_workflow_service.py
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, NotFound
from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance
from apps.attendance.models.employee_attendance_override import EmployeeAttendanceOverride
from apps.attendance.constants.hr_review_constants import HRReviewStatus

class HRReviewWorkflowService:
    """
    Orchestrates transaction-safe workflow adjustments on exception logs.
    Saves and preserves historical audit statements for every action.
    """

    @classmethod
    def _get_locked_summary_row(cls, company: Company, record_id: int) -> DailyAttendance:
        record = DailyAttendance.objects.filter(id=record_id, company=company).select_for_update().first()
        if not record:
            raise NotFound("The requested exception record was not found within this company workspace.")
        return record

    @classmethod
    def _log_audit_step(cls, company: Company, actor: Membership, record: DailyAttendance, field: str, old: str, new: str, note: str) -> None:
        """
        Internal log execution driver that hooks into your existing audit schema.
        """
        EmployeeAttendanceOverride.objects.create(
            company=company, daily_attendance=record, employee=record.membership,
            override_by=actor, field_name=f"REVIEW_{field}", old_value=old, new_value=new, reason=note
        )

    @classmethod
    @transaction.atomic
    def assign_reviewer_to_item(cls, *, company: Company, actor: Membership, record_id: int, reviewer_id: int, note: str) -> DailyAttendance:
        record = cls._get_locked_summary_row(company, record_id)
        
        target_reviewer = Membership.objects.filter(id=reviewer_id, company=company, is_active=True).first()
        if not target_reviewer:
            raise ValidationError("Assignment target error: Reviewer profile missing within this tenant context.")

        old_reviewer = str(record.finalized_by_id)
        record.finalized_by = target_reviewer
        record.save(update_fields=["finalized_by", "updated_at"])

        cls._log_audit_step(company, actor, record, "ASSIGNMENT", old_reviewer, str(reviewer_id), note)
        return record

    @classmethod
    @transaction.atomic
    def resolve_exception_item(cls, *, company: Company, actor: Membership, record_id: int, resolution_status: str, note: str) -> DailyAttendance:
        """
        Transitions exception rows to processed states.
        Clears review flags while preserving the original timeline integrity.
        """
        record = cls._get_locked_summary_row(company, record_id)
        
        if resolution_status not in [HRReviewStatus.RESOLVED, HRReviewStatus.REJECTED, HRReviewStatus.ESCALATED]:
            raise ValidationError("Workflow error: Target transition status is invalid.")

        old_flag_state = record.needs_review
        record.needs_review = (resolution_status == HRReviewStatus.ESCALATED)
        record.review_reason = f"Status resolution: {resolution_status}. Admin statement: {note}"
        
        if resolution_status == HRReviewStatus.RESOLVED:
            record.finalized_at = timezone.now()
            record.finalized_by = actor
            
        record.save(update_fields=["needs_review", "review_reason", "finalized_at", "finalized_by", "updated_at"])
        cls._log_audit_step(company, actor, record, "STATUS_RESOLUTION", str(old_flag_state), resolution_status, note)
        return record

    @classmethod
    @transaction.atomic
    def append_internal_review_note(cls, *, company: Company, actor: Membership, record_id: int, note_text: str) -> DailyAttendance:
        record = cls._get_locked_summary_row(company, record_id)
        
        if not note_text.strip():
            raise ValidationError("Validation error: Internal log statements cannot look blank.")

        old_narrative = record.review_reason
        # Format and append notes chronologically into the reason tracking column text
        timestamp_prefix = timezone.now().strftime("%Y-%m-%d %H:%M")
        record.review_reason = f"{old_narrative}\n[{timestamp_prefix} by {actor.user.username}]: {note_text}"
        record.save(update_fields=["review_reason", "updated_at"])

        cls._log_audit_step(company, actor, record, "INTERNAL_NOTE", "NarrativeAppend", note_text, "Appended discussion log.")
        return record