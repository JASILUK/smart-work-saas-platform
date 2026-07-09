# apps/attendance/services/hr_management_service.py
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceMethodChoices
from apps.attendance.services.daily_attendance_engine import DailyAttendanceEngine

class HRAttendanceManagementService:
    """
    Handles corporate timesheet modifications and payroll finalizations.
    Executes tasks inside explicit database transactions using row-level locks.
    """

    @classmethod
    def _append_audit_text(cls, record: DailyAttendance, action: str, actor: Membership, reason: str) -> str:
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        new_note = f"[{timestamp}] {action} by ID #{actor.id}. Reason: {reason}"
        if record.review_reason:
            return f"{record.review_reason}\n{new_note}"
        return new_note

    @classmethod
    @transaction.atomic
    def inject_manual_correction_event(
        cls, *, company: Company, admin_actor: Membership, target_member: Membership, data: dict
    ) -> AttendanceEvent:
        target_date = data["attendance_date"]
        
        sheet = DailyAttendance.objects.filter(
            company=company, membership=target_member, attendance_date=target_date
        ).select_for_update().first()

        if sheet and sheet.finalized_at:
            raise ValidationError("Modifications blocked: This attendance sheet is finalized for payroll.")

        event = AttendanceEvent.objects.create(
            company=company,
            membership=target_member,
            event_type=data["event_type"],
            attendance_method=AttendanceMethodChoices.MANUAL,
            event_time=data["event_time"],
            notes=data["reason"],
            created_by=admin_actor,
            is_system_generated=False,
            verification_payload={"executed_by_admin_id": admin_actor.id}
        )

        # Trigger background recalculations
        sheet = DailyAttendanceEngine.build_daily_attendance(
            company=company, membership=target_member, target_date=target_date
        )

        # Append inline audit string notes directly onto the ledger row
        sheet.review_reason = cls._append_audit_text(
            record=sheet, 
            action="MANUAL_CORRECTION_INJECTED", 
            actor=admin_actor, 
            reason=data["reason"]
        )
        sheet.save(update_fields=["review_reason"])
        return event

    @classmethod
    @transaction.atomic
    def finalize_record(cls, *, company: Company, admin_actor: Membership, record_id: int, reason: str) -> DailyAttendance:
        record = DailyAttendance.objects.filter(id=record_id, company=company).select_for_update().first()
        if not record:
            raise ValidationError("Daily attendance record not found.")
        if record.needs_review:
            raise ValidationError("Cannot finalize a record with outstanding unresolved HR review flags.")
        if record.finalized_at:
            raise ValidationError("Record has already been marked as finalized.")

        record.finalized_at = timezone.now()
        record.finalized_by = admin_actor
        record.review_reason = cls._append_audit_text(record, "RECORD_FINALIZED", admin_actor, reason)
        record.save(update_fields=["finalized_at", "finalized_by", "review_reason", "updated_at"])
        return record

    @classmethod
    @transaction.atomic
    def unlock_record(cls, *, company: Company, admin_actor: Membership, record_id: int, reason: str) -> DailyAttendance:
        record = DailyAttendance.objects.filter(id=record_id, company=company).select_for_update().first()
        if not record:
            raise ValidationError("Daily attendance record not found.")
        if not record.finalized_at:
            raise ValidationError("Record is already unlocked.")

        record.finalized_at = None
        record.finalized_by = None
        record.review_reason = cls._append_audit_text(record, "RECORD_UNLOCKED", admin_actor, reason)
        record.save(update_fields=["finalized_at", "finalized_by", "review_reason", "updated_at"])
        return record

    @classmethod
    @transaction.atomic
    def reprocess_record_timeline(cls, *, company: Company, admin_actor: Membership, record_id: int, reason: str) -> DailyAttendance:
        record = DailyAttendance.objects.filter(id=record_id, company=company).select_for_update().first()
        if not record:
            raise ValidationError("Daily attendance record not found.")
        if record.finalized_at:
            raise ValidationError("Reprocessing blocked: Record is locked for payroll processing.")

        computed_record = DailyAttendanceEngine.build_daily_attendance(
            company=company, membership=record.membership, target_date=record.attendance_date
        )

        computed_record.review_reason = cls._append_audit_text(computed_record, "TIMELINE_REPROCESSED", admin_actor, reason)
        computed_record.save(update_fields=["review_reason"])
        return computed_record