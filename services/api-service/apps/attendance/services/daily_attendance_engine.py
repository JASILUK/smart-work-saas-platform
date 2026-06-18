import datetime
import django.utils.timezone as timezone
from typing import Any, Dict, List, Optional
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _

from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance, DailyAttendanceStatus, DailyAttendanceInflowSource
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceEventTypes
from apps.attendance.selectors.daily_attendance_selector import DailyAttendanceSelector


class DailyAttendanceEngine:
    """
    The processing hub of the multi-tenant tracking framework.
    Translates raw streaming punch sequences into immutable daily evaluation records.
    """

    @classmethod
    @transaction.atomic
    def build_daily_attendance(cls, *, company: Company, membership: Membership, target_date: datetime.date) -> DailyAttendance:
        """
        Processes timeline analytics for a specific employee date segment.
        """
        # Purge pre-existing unfinalized calculations records to ensure execution idempotency safely
        existing_record = DailyAttendanceSelector.get_for_employee_date(company=company, membership=membership, target_date=target_date)
        if existing_record and existing_record.finalized_at:
            raise DjangoValidationError(_("Cannot modify metrics parameters. Payroll boundaries for this daily record are finalized."))

        if existing_record:
            existing_record.delete()

        # Step 1: Extract transaction stream data logs
        events = list(AttendanceEvent.objects.filter(
            company=company, membership=membership, event_time__date=target_date
        ).order_by("event_time"))

        # Step 2: Initialize organizational baseline snapshots config models
        schedule = cls._mock_resolve_schedule(company, membership, target_date)
        policy = cls._mock_resolve_policy(company, membership, target_date)

        # Step 3: Branch evaluation processing states down specialized logic tracks
        is_weekend = cls._mock_eval_weekend(membership, target_date)
        is_holiday = cls._mock_eval_holiday(company, target_date)
        is_leave = cls._mock_eval_leave(membership, target_date)

        record = DailyAttendance(
            company=company, membership=membership, attendance_date=target_date,
            schedule_snapshot=schedule, policy_snapshot=policy,
            is_weekend=is_weekend, is_holiday=is_holiday, is_leave=is_leave,
            required_work_minutes=policy["required_work_minutes"]
        )

        if is_leave:
            record.attendance_status = DailyAttendanceStatus.LEAVE
            record.is_absent = False
            record.save()
            return record

        if is_holiday:
            record.attendance_status = DailyAttendanceStatus.HOLIDAY
            record.is_absent = False
            record.save()
            return record

        if is_weekend:
            record.attendance_status = DailyAttendanceStatus.WEEKEND
            record.is_absent = False
            record.save()
            return record

        # Fallback to absent verification routing checks if timelines look empty
        if not events:
            record.attendance_status = DailyAttendanceStatus.ABSENT
            record.is_absent = True
            record.save()
            return record

        # Process active logs timeline parameters mapping tracking boundaries
        ins = [e for e in events if e.event_type == AttendanceEventTypes.CHECK_IN]
        outs = [e for e in events if e.event_type == AttendanceEventTypes.CHECK_OUT]

        record.first_check_in_at = ins[0].event_time if ins else None
        record.last_check_out_at = outs[-1].event_time if outs else None

        # Check for open missing terminal check-out exception conditions structures
        if record.first_check_in_at and not record.last_check_out_at:
            record.attendance_status = DailyAttendanceStatus.INCOMPLETE
            record.needs_review = True
            record.review_reason = "Missing checkout event signature detected on daily tracker array."
            record.save()
            return record

        # Compute intervals work ranges parameters
        record.total_break_minutes = cls.calculate_break_minutes(events)
        record.total_work_minutes = cls.calculate_work_minutes(record.first_check_in_at, record.last_check_out_at, record.total_break_minutes)

        # Execute metric drift evaluation offsets loops
        cls.determine_lateness(record, schedule, policy)
        cls.determine_early_exit(record, schedule, policy)
        cls.determine_overtime(record, policy)
        cls.determine_status(record, policy)

        record.save()
        return record

    @classmethod
    def calculate_break_minutes(cls, events: List[AttendanceEvent]) -> int:
        total = 0
        starts = [e for e in events if e.event_type == AttendanceEventTypes.BREAK_OUT]
        ends = [e for e in events if e.event_type == AttendanceEventTypes.BREAK_IN]
        
        for s, e in zip(starts, ends):
            diff = (e.event_time - s.event_time).total_seconds() / 60
            if diff > 0:
                total += int(diff)
        return total

    @classmethod
    def calculate_work_minutes(cls, check_in, check_out, break_mins: int) -> int:
        if not check_in or not check_out:
            return 0
        gross = (check_out - check_in).total_seconds() / 60
        net = gross - break_mins
        return max(0, int(net))

    @classmethod
    def determine_lateness(cls, record: DailyAttendance, schedule: dict, policy: dict) -> None:
        if not record.first_check_in_at:
            return
        
        # Convert timezone timestamps to local strings matching formatting indices
        checkin_time_str = record.first_check_in_at.astimezone().strftime("%H:%M")
        start_target = datetime.datetime.strptime(schedule["work_start_time"], "%H:%M")
        actual_time = datetime.datetime.strptime(checkin_time_str, "%H:%M")
        
        drift = (actual_time - start_target).total_seconds() / 60
        if drift > policy["late_after_minutes"]:
            record.is_late = True
            record.late_minutes = int(drift)

    @classmethod
    def determine_early_exit(cls, record: DailyAttendance, schedule: dict, policy: dict) -> None:
        if not record.last_check_out_at:
            return
            
        checkout_time_str = record.last_check_out_at.astimezone().strftime("%H:%M")
        end_target = datetime.datetime.strptime(schedule["work_end_time"], "%H:%M")
        actual_time = datetime.datetime.strptime(checkout_time_str, "%H:%M")
        
        drift = (end_target - actual_time).total_seconds() / 60
        if drift > policy["early_exit_before_minutes"]:
            record.is_early_exit = True
            record.early_exit_minutes = int(drift)

    @classmethod
    def determine_overtime(cls, record: DailyAttendance, policy: dict) -> None:
        if not policy["overtime_enabled"]:
            return
        if record.total_work_minutes > policy["overtime_after_minutes"]:
            record.overtime_minutes = record.total_work_minutes - policy["overtime_after_minutes"]

    @classmethod
    def determine_status(cls, record: DailyAttendance, policy: dict) -> None:
        if record.total_work_minutes < policy["half_day_below_minutes"]:
            record.attendance_status = DailyAttendanceStatus.ABSENT
            record.is_absent = True
            record.is_present = False
        elif record.total_work_minutes < policy["required_work_minutes"]:
            record.attendance_status = DailyAttendanceStatus.HALF_DAY
            record.is_half_day = True
            record.is_absent = False
            record.is_present = False
        else:
            record.attendance_status = DailyAttendanceStatus.PRESENT
            record.is_present = True
            record.is_absent = False

    @classmethod
    @transaction.atomic
    def finalize_attendance(cls, *, record: DailyAttendance, auditor: Membership) -> DailyAttendance:
        if record.needs_review:
            raise DjangoValidationError(_("Cannot finalize entry records containing unresolved HR alerts indicators flags."))
        record.finalized_at = timezone.now()
        record.finalized_by = auditor
        record.save(update_fields=["finalized_at", "finalized_by", "updated_at"])
        return record

    @classmethod
    @transaction.atomic
    def reprocess_attendance(cls, *, company: Company, membership: Membership, target_date: datetime.date, actor: Membership) -> DailyAttendance:
        record = DailyAttendanceSelector.get_for_employee_date(company=company, membership=membership, target_date=target_date)
        if record and record.finalized_at:
            # Explicit unlocking track bypass block used for direct manual recalculation overrides
            record.finalized_at = None
            record.save(update_fields=["finalized_at"])
            
        new_record = cls.build_daily_attendance(company=company, membership=membership, target_date=target_date)
        new_record.source = DailyAttendanceInflowSource.REPROCESSED
        new_record.save(update_fields=["source"])
        return new_record

    @classmethod
    @transaction.atomic
    def auto_finalize_missing_checkout(cls, *, company: Company, target_date: datetime.date) -> int:
        """
        Scans incomplete configurations, applying auto-checkout logic to unclosed shift records.
        """
        records = DailyAttendance.objects.filter(company=company, attendance_date=target_date, attendance_status=DailyAttendanceStatus.INCOMPLETE, is_auto_closed=False)
        count = 0
        for rec in records:
            rec.is_auto_closed = True
            rec.auto_close_reason = "System automated tracking closure. Missing boundary timeout triggered."
            rec.attendance_status = DailyAttendanceStatus.HALF_DAY  # Apply automated safety deduction rules
            rec.save()
            count += 1
        return count

    # Mock parameters orchestration routes bypass components
    @classmethod
    def _mock_resolve_schedule(cls, c, m, d): return {"work_start_time": "09:00", "work_end_time": "18:00", "break_minutes": 60}
    @classmethod
    def _mock_resolve_policy(cls, c, m, d): return {"required_work_minutes": 480, "half_day_below_minutes": 240, "late_after_minutes": 15, "early_exit_before_minutes": 15, "overtime_enabled": True, "overtime_after_minutes": 480}
    @classmethod
    def _mock_eval_weekend(cls, m, d): return d.weekday() in [5, 6]
    @classmethod
    def _mock_eval_holiday(cls, c, d): return False
    @classmethod
    def _mock_eval_leave(cls, m, d): return False