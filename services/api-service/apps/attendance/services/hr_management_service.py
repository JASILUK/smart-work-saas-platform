from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceMethodChoices
from apps.attendance.models.employee_attendance_override import EmployeeAttendanceOverride
from apps.attendance.services.daily_attendance_engine import DailyAttendanceEngine
from apps.attendance.constants.hr_foundation_constants import HRAuditActionChoices

class HRAttendanceManagementService:
    """
    Handles corporate timesheet modifications and payroll finalizations.
    Executes tasks inside explicit database transactions using row-level constraints.
    """

    @classmethod
    def _write_audit_log(
        cls,
        *,
        company: Company,
        admin_actor: Membership,
        record: DailyAttendance,
        action: HRAuditActionChoices,
        old_state: str,
        new_state: str,
        reason: str
    ) -> EmployeeAttendanceOverride:
        """
        Internal helper that writes modifications to the append-only corporate audit trail.
        Uses your existing enterprise `EmployeeAttendanceOverride` model architecture.
        """
        return EmployeeAttendanceOverride.objects.create(
            company=company,
            daily_attendance=record,
            employee=record.membership,  # Maps directly to the target membership line
            override_by=admin_actor,
            field_name=action,
            old_value=old_state,
            new_value=new_state,
            reason=reason
        )

    @classmethod
    @transaction.atomic
    def inject_manual_correction_event(
        cls, *, company: Company, admin_actor: Membership, target_member: Membership, data: dict
    ) -> AttendanceEvent:
        """
        Safely injects a manual override tracking entry into an active log stream.
        Triggers a timeline recalculation via the legacy engine right after registration.
        """
        target_date = data["attendance_date"]
        
        # Prevent data races by locking the target row before validation checks
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

        # Safely hand calculation off to the legacy generation pipeline
        DailyAttendanceEngine.build_daily_attendance(
            company=company, membership=target_member, target_date=target_date
        )

        # Refresh state data after engine processing to log an accurate audit snapshot
        if sheet:
            sheet.refresh_from_db()
            cls._write_audit_log(
                company=company,
                admin_actor=admin_actor,
                record=sheet,
                action=HRAuditActionChoices.MANUAL_CORRECTION,
                old_state="STATE_BEFORE_INJECTION",
                new_state=f"Event Added: {data['event_type']} @ {data['event_time']}",
                reason=data["reason"]
            )
        return event

    @classmethod
    @transaction.atomic
    def finalize_record(cls, *, company: Company, admin_actor: Membership, record_id: int, reason: str) -> DailyAttendance:
        """
        Applies a definitive payroll lock onto a specified daily tracking entry.
        """
        record = DailyAttendance.objects.filter(id=record_id, company=company).select_for_update().first()
        if not record:
            raise ValidationError("Daily attendance record not traced.")
        if record.needs_review:
            raise ValidationError("Cannot finalize a record with outstanding unresolved HR review flags.")
        if record.finalized_at:
            raise ValidationError("Record has already been marked as finalized.")

        old_timestamp = str(record.finalized_at)
        record.finalized_at = timezone.now()
        record.finalized_by = admin_actor
        record.save(update_fields=["finalized_at", "finalized_by", "updated_at"])

        cls._write_audit_log(
            company=company,
            admin_actor=admin_actor,
            record=record,
            action=HRAuditActionChoices.RECORD_FINALIZE,
            old_state=old_timestamp,
            new_state=f"Locked at: {record.finalized_at} by ID: {admin_actor.id}",
            reason=reason
        )
        return record

    @classmethod
    @transaction.atomic
    def unlock_record(cls, *, company: Company, admin_actor: Membership, record_id: int, reason: str) -> DailyAttendance:
        """
        Removes payroll finalization locks from a specified ledger entry.
        """
        record = DailyAttendance.objects.filter(id=record_id, company=company).select_for_update().first()
        if not record:
            raise ValidationError("Daily attendance record not traced.")
        if not record.finalized_at:
            raise ValidationError("Record is already unlocked.")

        old_state_marker = f"Locked by Admin ID: {record.finalized_by_id} at {record.finalized_at}"
        record.finalized_at = None
        record.finalized_by = None
        record.save(update_fields=["finalized_at", "finalized_by", "updated_at"])

        cls._write_audit_log(
            company=company,
            admin_actor=admin_actor,
            record=record,
            action=HRAuditActionChoices.RECORD_UNLOCK,
            old_state=old_state_marker,
            new_state="UNLOCKED_NULL_STATE",
            reason=reason
        )
        return record

    @classmethod
    @transaction.atomic
    def reprocess_record_timeline(cls, *, company: Company, admin_actor: Membership, record_id: int, reason: str) -> DailyAttendance:
        """
        Forces the core system to re-evaluate tracking history configurations.
        """
        record = DailyAttendance.objects.filter(id=record_id, company=company).select_for_update().first()
        if not record:
            raise ValidationError("Daily attendance record not traced.")
        if record.finalized_at:
            raise ValidationError("Reprocessing blocked: Record is locked for payroll processing.")

        old_status = str(record.attendance_status)
        
        computed_record = DailyAttendanceEngine.build_daily_attendance(
            company=company, membership=record.membership, target_date=record.attendance_date
        )

        cls._write_audit_log(
            company=company,
            admin_actor=admin_actor,
            record=computed_record,
            action=HRAuditActionChoices.TIMELINE_REPROCESS,
            old_state=f"Status: {old_status}",
            new_state=f"Status Post-Processing: {computed_record.attendance_status}",
            reason=reason
        )
        return computed_record