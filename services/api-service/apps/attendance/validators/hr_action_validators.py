# apps/attendance/validators/hr_action_validators.py
import datetime
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance, DailyAttendanceStatus
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceEventTypes

class HRAttendanceActionValidator:
    """
    Centralizes domain invariants, status validation transitions, 
    and multi-tenant verification checks for administrative mutations.
    """

    @staticmethod
    def validate_editable_state(record: DailyAttendance) -> None:
        """
        Asserts that a record has not been finalized and frozen for corporate payroll.
        """
        if record.finalized_at is not None:
            raise ValidationError("Action blocked: This attendance sheet is finalized and locked for payroll processing.")

    @staticmethod
    def validate_event_time_bounds(event_time: datetime.datetime, target_date: datetime.date) -> None:
        """
        Ensures that an administrative punch matches the logical target date and does not occur in the future.
        """
        if event_time > timezone.now():
            raise ValidationError("Action validation error: Punch timestamps cannot exist in the future.")
        if event_time.date() != target_date:
            raise ValidationError("Action validation error: Punch timestamp must fall within the target calendar date context.")

    @staticmethod
    def validate_punch_sequence(record: DailyAttendance, proposed_type: str, event_time: datetime.datetime) -> None:
        """
        Validates chronological sequencing to prevent double check-ins, out-of-order breaks, or double check-outs.
        """
        # Fetch existing chronological events for the target day context
        existing_events = AttendanceEvent.objects.filter(
            company=record.company,
            membership=record.membership,
            event_time__date=record.attendance_date
        ).order_by("event_time")

        if proposed_type == AttendanceEventTypes.CHECK_IN:
            if record.first_check_in_at is not None or existing_events.filter(event_type=AttendanceEventTypes.CHECK_IN).exists():
                raise ValidationError("Sequence violation: Employee is already checked in for this date.")

        if proposed_type == AttendanceEventTypes.CHECK_OUT:
            if record.first_check_in_at is None:
                raise ValidationError("Sequence violation: Cannot process check-out without an existing check-in log.")
            if record.last_check_out_at is not None or existing_events.filter(event_type=AttendanceEventTypes.CHECK_OUT).exists():
                raise ValidationError("Sequence violation: Employee has already checked out for this date.")
            
            # Verify that checkout time succeeds the initial check-in time
            if record.first_check_in_at and event_time <= record.first_check_in_at:
                raise ValidationError("Sequence violation: Check-out time must follow the original check-in timestamp.")

        if proposed_type in [AttendanceEventTypes.BREAK_OUT, AttendanceEventTypes.BREAK_IN]:
            if record.first_check_in_at is None or record.last_check_out_at is not None:
                raise ValidationError("Sequence violation: Breaks can only be recorded during an active shift window.")

    @staticmethod
    def validate_status_transition(current_status: str, proposed_status: str) -> None:
        """
        Enforces valid state transition matrices for administrative status overrides.
        """
        if current_status == proposed_status:
            raise ValidationError(f"State identity collision: The record status is already marked as {proposed_status}.")
        
        valid_statuses = [choice[0] for choice in DailyAttendanceStatus.choices]
        if proposed_status not in valid_statuses:
            raise ValidationError(f"Invalid status value parameter variable target: {proposed_status}")