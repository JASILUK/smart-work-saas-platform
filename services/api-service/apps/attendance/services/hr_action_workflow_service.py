# apps/attendance/services/hr_action_workflow_service.py
import datetime
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, NotFound
from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance, DailyAttendanceStatus, DailyAttendanceInflowSource
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceMethodChoices, AttendanceEventTypes
from apps.attendance.models.employee_attendance_override import EmployeeAttendanceOverride
from apps.attendance.services.daily_attendance_engine import DailyAttendanceEngine
from apps.attendance.validators.hr_action_validators import HRAttendanceActionValidator

class HRAttendanceActionWorkflowService:
    """
    Executes transaction-safe administrative adjustments on attendance records.
    Every operation applies explicit row-level locks and registers a comprehensive audit footprint.
    """

    @classmethod
    def _get_locked_record(cls, company: Company, record_id: int) -> DailyAttendance:
        """
        Helper method that fetches a target row using an explicit select_for_update database lock.
        """
        record = DailyAttendance.objects.filter(id=record_id, company=company).select_for_update().first()
        if not record:
            raise NotFound("The requested daily attendance record was not found within this company workspace context.")
        return record

    @classmethod
    def _create_audit_log(
        cls, *, company: Company, actor: Membership, record: DailyAttendance, action: str, old: str, new: str, reason: str
    ) -> None:
        """
        Saves record modifications to the append-only operational audit log ledger.
        """
        EmployeeAttendanceOverride.objects.create(
            company=company,
            daily_attendance=record,
            employee=record.membership,
            override_by=actor,
            field_name=action,
            old_value=str(old),
            new_value=str(new),
            reason=reason
        )

    @classmethod
    @transaction.atomic
    def execute_manual_check_in(cls, *, company: Company, actor: Membership, record_id: int, data: dict) -> DailyAttendance:
        record = cls._get_locked_record(company, record_id)
        HRAttendanceActionValidator.validate_editable_state(record)
        
        punch_time = data["event_time"]
        HRAttendanceActionValidator.validate_event_time_bounds(punch_time, record.attendance_date)
        HRAttendanceActionValidator.validate_punch_sequence(record, AttendanceEventTypes.CHECK_IN, punch_time)

        # 1. Persist the new manual action event
        AttendanceEvent.objects.create(
            company=company, membership=record.membership, event_type=AttendanceEventTypes.CHECK_IN,
            attendance_method=AttendanceMethodChoices.MANUAL, event_time=punch_time,
            notes=data["reason"], created_by=actor, is_system_generated=False
        )

        # 2. Re-evaluate metrics via the legacy calculation engine pipeline
        DailyAttendanceEngine.build_daily_attendance(company=company, membership=record.membership, target_date=record.attendance_date)
        
        record.refresh_from_db()
        cls._create_audit_log(company=company, actor=actor, record=record, action="MANUAL_CHECK_IN", old="None", new=str(punch_time), reason=data["reason"])
        return record

    @classmethod
    @transaction.atomic
    def execute_manual_check_out(cls, *, company: Company, actor: Membership, record_id: int, data: dict) -> DailyAttendance:
        record = cls._get_locked_record(company, record_id)
        HRAttendanceActionValidator.validate_editable_state(record)
        
        punch_time = data["event_time"]
        HRAttendanceActionValidator.validate_event_time_bounds(punch_time, record.attendance_date)
        HRAttendanceActionValidator.validate_punch_sequence(record, AttendanceEventTypes.CHECK_OUT, punch_time)

        AttendanceEvent.objects.create(
            company=company, membership=record.membership, event_type=AttendanceEventTypes.CHECK_OUT,
            attendance_method=AttendanceMethodChoices.MANUAL, event_time=punch_time,
            notes=data["reason"], created_by=actor, is_system_generated=False
        )

        DailyAttendanceEngine.build_daily_attendance(company=company, membership=record.membership, target_date=record.attendance_date)
        
        record.refresh_from_db()
        cls._create_audit_log(company=company, actor=actor, record=record, action="MANUAL_CHECK_OUT", old="None", new=str(punch_time), reason=data["reason"])
        return record

    @classmethod
    @transaction.atomic
    def execute_manual_break_action(cls, *, company: Company, actor: Membership, record_id: int, action_type: str, data: dict) -> DailyAttendance:
        record = cls._get_locked_record(company, record_id)
        HRAttendanceActionValidator.validate_editable_state(record)
        
        punch_time = data["event_time"]
        HRAttendanceActionValidator.validate_event_time_bounds(punch_time, record.attendance_date)
        HRAttendanceActionValidator.validate_punch_sequence(record, action_type, punch_time)

        AttendanceEvent.objects.create(
            company=company, membership=record.membership, event_type=action_type,
            attendance_method=AttendanceMethodChoices.MANUAL, event_time=punch_time,
            notes=data["reason"], created_by=actor, is_system_generated=False
        )

        DailyAttendanceEngine.build_daily_attendance(company=company, membership=record.membership, target_date=record.attendance_date)
        
        record.refresh_from_db()
        cls._create_audit_log(company=company, actor=actor, record=record, action=f"MANUAL_{action_type}", old="None", new=str(punch_time), reason=data["reason"])
        return record

    @classmethod
    @transaction.atomic
    def execute_status_override(cls, *, company: Company, actor: Membership, record_id: int, data: dict) -> DailyAttendance:
        record = cls._get_locked_record(company, record_id)
        HRAttendanceActionValidator.validate_editable_state(record)
        
        proposed_status = data["target_status"]
        HRAttendanceActionValidator.validate_status_transition(record.attendance_status, proposed_status)

        old_status = record.attendance_status
        record.attendance_status = proposed_status
        record.source = DailyAttendanceInflowSource.MANUAL
        
        # Synchronize model boolean flags dynamically based on the target selection status
        record.is_present = proposed_status in [DailyAttendanceStatus.PRESENT, "LATE"]
        record.is_absent = proposed_status == DailyAttendanceStatus.ABSENT
        record.is_half_day = proposed_status == DailyAttendanceStatus.HALF_DAY
        record.is_leave = proposed_status == DailyAttendanceStatus.LEAVE
        record.is_holiday = proposed_status == DailyAttendanceStatus.HOLIDAY
        record.is_weekend = proposed_status == DailyAttendanceStatus.WEEKEND
        
        record.save()
        cls._create_audit_log(company=company, actor=actor, record=record, action="STATUS_OVERRIDE", old=old_status, new=proposed_status, reason=data["reason"])
        return record

    @classmethod
    @transaction.atomic
    def execute_finalize(cls, *, company: Company, actor: Membership, record_id: int, data: dict) -> DailyAttendance:
        record = cls._get_locked_record(company, record_id)
        if record.finalized_at is not None:
            raise ValidationError("Action identity collision: This attendance sheet is already finalized.")
        if record.needs_review:
            raise ValidationError("Finalization blocked: Outstanding unresolved HR review flags must be cleared first.")

        record.finalized_at = timezone.now()
        record.finalized_by = actor
        record.save(update_fields=["finalized_at", "finalized_by", "updated_at"])

        cls._create_audit_log(company=company, actor=actor, record=record, action="FINALIZATION_LOCK", old="Unlocked", new=f"Locked at {record.finalized_at}", reason=data["reason"])
        return record

    @classmethod
    @transaction.atomic
    def execute_unlock(cls, *, company: Company, actor: Membership, record_id: int, data: dict) -> DailyAttendance:
        record = cls._get_locked_record(company, record_id)
        if record.finalized_at is None:
            raise ValidationError("Action identity collision: This attendance sheet is already unlocked.")

        old_lock_timestamp = record.finalized_at
        record.finalized_at = None
        record.finalized_by = None
        record.save(update_fields=["finalized_at", "finalized_by", "updated_at"])

        cls._create_audit_log(company=company, actor=actor, record=record, action="FINALIZATION_UNLOCK", old=str(old_lock_timestamp), new="Unlocked", reason=data["reason"])
        return record

    @classmethod
    @transaction.atomic
    def execute_reprocess_or_recalculate(cls, *, company: Company, actor: Membership, record_id: int, data: dict) -> DailyAttendance:
        record = cls._get_locked_record(company, record_id)
        HRAttendanceActionValidator.validate_editable_state(record)

        old_status = record.attendance_status
        
        # Delegate re-evaluations safely to your legacy engine architecture
        DailyAttendanceEngine.build_daily_attendance(company=company, membership=record.membership, target_date=record.attendance_date)
        
        record.refresh_from_db()
        cls._create_audit_log(company=company, actor=actor, record=record, action="TIMELINE_REPROCESS", old=old_status, new=record.attendance_status, reason=data["reason"])
        return record

    @classmethod
    @transaction.atomic
    def execute_review_toggle(cls, *, company: Company, actor: Membership, record_id: int, set_flag: bool, data: dict) -> DailyAttendance:
        record = cls._get_locked_record(company, record_id)
        HRAttendanceActionValidator.validate_editable_state(record)

        old_flag = record.needs_review
        record.needs_review = set_flag
        record.review_reason = data["reason"] if set_flag else f"Cleared by Admin ID #{actor.id}. Notes: {data['reason']}"
        record.save(update_fields=["needs_review", "review_reason", "updated_at"])

        cls._create_audit_log(company=company, actor=actor, record=record, action="REVIEW_FLAG_TOGGLE", old=str(old_flag), new=str(set_flag), reason=data["reason"])
        return record