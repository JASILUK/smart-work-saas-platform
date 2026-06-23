import datetime
import pytz
from typing import Optional
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from apps.attendance.selectors.employee_shift_assignment_selectors import EmployeeShiftAssignmentSelector
from apps.attendance.selectors.company_work_schedule_selector import CompanyWorkScheduleSelector


class ShiftTimeValidator:
    """
    Simple real-world shift time validation.
    - Check-in: Can't be after shift ends
    - Check-out: Can't be before shift starts
    """

    @classmethod
    def get_company_tz(cls, company) -> pytz.timezone:
        """Resolve company timezone."""
        ws = CompanyWorkScheduleSelector.get_by_company(company=company)
        if ws and getattr(ws, 'timezone', None):
            return pytz.timezone(ws.timezone)
        if getattr(company, 'timezone', None):
            return pytz.timezone(company.timezone)
        return pytz.UTC

    @classmethod
    def get_current_shift(cls, membership, target_date=None) -> Optional:
        """Get active shift for employee."""
        if target_date is None:
            target_date = timezone.localtime(timezone.now()).date()
        
        assignment = EmployeeShiftAssignmentSelector.get_active_assignment_for_date(
            membership=membership, date=target_date
        )
        if assignment and getattr(assignment, 'shift', None):
            return assignment.shift
        
        ws = CompanyWorkScheduleSelector.get_by_company(company=membership.company)
        if ws and getattr(ws, 'default_shift', None):
            return ws.default_shift
        
        return None

    @classmethod
    def is_night_shift(cls, shift) -> bool:
        """Shift crosses midnight?"""
        if getattr(shift, 'is_night_shift', False):
            return True
        return shift.end_time < shift.start_time

    @classmethod
    def validate_check_in(cls, *, company, membership):
        """
        Check-in rules:
        - Can be anytime BEFORE shift end
        - Can't check in AFTER shift has finished
        """
        shift = cls.get_current_shift(membership)
        if not shift:
            return  # No shift, no restriction
        
        tz = cls.get_company_tz(company)
        now = timezone.localtime(timezone.now(), tz)
        current_time = now.time()
        is_night = cls.is_night_shift(shift)
        
        start_str = shift.start_time.strftime('%I:%M %p')
        end_str = shift.end_time.strftime('%I:%M %p')
        
        # Night shift (22:00 → 06:00): Can't check in after 06:00
        if is_night:
            if shift.end_time < shift.start_time:  # 06:00 < 22:00
                if current_time > shift.end_time and current_time < shift.start_time:
                    raise DjangoValidationError(
                        _(f"Your night shift ({start_str} - {end_str}) has ended. Next shift starts at {start_str}.")
                    )
        else:
            # Day shift: Can't check in after shift end
            if current_time > shift.end_time:
                raise DjangoValidationError(
                    _(f"Shift has ended at {end_str}. Cannot check in.")
                )

    @classmethod
    def validate_check_out(cls, *, company, membership):
        """
        Check-out rules:
        - Can't check out before shift starts
        """
        shift = cls.get_current_shift(membership)
        if not shift:
            return
        
        tz = cls.get_company_tz(company)
        now = timezone.localtime(timezone.now(), tz)
        current_time = now.time()
        is_night = cls.is_night_shift(shift)
        
        start_str = shift.start_time.strftime('%I:%M %p')
        end_str = shift.end_time.strftime('%I:%M %p')
        
        if not is_night:
            # Day shift: Can't check out before shift starts
            if current_time < shift.start_time:
                raise DjangoValidationError(
                    _(f"Cannot check out before shift starts at {start_str}.")
                )