# apps/attendance/selectors/attendance_event_selector.py
import datetime
import zoneinfo
from typing import Optional
from django.db.models import QuerySet, Q
from django.utils import timezone
from apps.companies.models import Company, Membership
from apps.attendance.models.attendance_event import AttendanceEvent

# Import the shift selectors to dynamically check assignments
from apps.attendance.selectors.shift_selector import ShiftSelector
from apps.attendance.selectors.employee_shift_assignment_selectors import EmployeeShiftAssignmentSelector


class AttendanceEventSelector:
    """
    Optimized data access selectors for Attendance Events.
    Dynamically computes shift-schedule aware database query boundaries.
    """
    @classmethod
    def get_queryset(cls) -> QuerySet[AttendanceEvent]:
        return AttendanceEvent.objects.select_related(
            "membership__user", "membership__department", "location", "face_enrollment"
        )

    @classmethod
    def get_by_id(cls, *, event_id: int, company: Company) -> Optional[AttendanceEvent]:
        return cls.get_queryset().filter(id=event_id, company=company).first()

    @classmethod
    def _get_company_timezone(cls, company: Company) -> zoneinfo.ZoneInfo:
        """Helper utility to resolve company specific ZoneInfo securely."""
        company_tz_str = getattr(company, "timezone", "UTC")
        try:
            return zoneinfo.ZoneInfo(company_tz_str)
        except Exception:
            return zoneinfo.ZoneInfo("UTC")

    @classmethod
    def _get_shift_aware_utc_range(cls, membership: Membership, target_date: datetime.date) -> tuple:
        """
        Calculates a dynamic time window based on the employee's assigned shift.
        Extends boundaries safely if evaluating a night shift rollover.
        """
        company = membership.company
        local_zone = cls._get_company_timezone(company)
        tz_default = timezone.get_default_timezone()

        # Step A: Resolve the active shift schedule (Assignment -> Company DefaultFallback)
        assignment = EmployeeShiftAssignmentSelector.get_active_assignment_for_date(
            membership=membership, 
            date=target_date
        )
        
        if assignment and assignment.shift and assignment.shift.is_active:
            active_shift = assignment.shift
        else:
            active_shift = ShiftSelector.get_default_shift(company=company)

        # Step B: Establish localized baseline times
        start_local = datetime.datetime.combine(target_date, datetime.time.min)
        
        # If it's a night shift, extend the calculation window into the next calendar day 
        # (e.g., until 12:00 PM noon the next day) to capture the overnight rollover punches cleanly.
        if active_shift and active_shift.is_night_shift:
            end_local = datetime.datetime.combine(target_date + datetime.timedelta(days=1), datetime.time(12, 0))
        else:
            end_local = datetime.datetime.combine(target_date, datetime.time.max)

        # Step C: Translate the localized local boundaries cleanly into UTC timestamps
        start_utc = timezone.make_aware(start_local, tz_default).astimezone(timezone.utc)
        end_utc = timezone.make_aware(end_local, tz_default).astimezone(timezone.utc)
        
        return start_utc, end_utc

    @classmethod
    def get_latest_event(cls, *, company: Company, membership: Membership, target_date: Optional[datetime.date] = None) -> Optional[AttendanceEvent]:
        """Fetches the latest recorded punch card action for an employee profile."""
        queryset = cls.get_queryset().filter(company=company, membership=membership)
        if target_date:
            start_utc, end_utc = cls._get_shift_aware_utc_range(membership, target_date)
            queryset = queryset.filter(event_time__range=(start_utc, end_utc))
        return queryset.order_by("-event_time", "-id").first()

    @classmethod
    def get_today_events(cls, *, company: Company, membership: Membership) -> QuerySet[AttendanceEvent]:
        """Fetches live operational logs tracking today's active window."""
        local_zone = cls._get_company_timezone(company)
        today_local = timezone.localtime(timezone.now(), local_zone).date()
        return cls.get_events_for_membership_and_date(membership=membership, date=today_local)

    @classmethod
    def get_events_for_membership_and_date(cls, *, membership: Membership, date: datetime.date) -> QuerySet[AttendanceEvent]:
        """
        Extracts punch timelines securely without local timezone offset or 
        cross-midnight rollover boundary clipping errors.
        """
        start_utc, end_utc = cls._get_shift_aware_utc_range(membership, date)
        return cls.get_queryset().filter(
            company=membership.company, 
            membership=membership, 
            event_time__range=(start_utc, end_utc)
        ).order_by("event_time")

    @classmethod
    def get_membership_events(cls, *, company: Company, membership: Membership, start_date: datetime.date, end_date: datetime.date) -> QuerySet[AttendanceEvent]:
        """Extract complete event matrices across multi-date windows."""
        start_utc, _ = cls._get_shift_aware_utc_range(membership, start_date)
        _, end_utc = cls._get_shift_aware_utc_range(membership, end_date)
        return cls.get_queryset().filter(
            company=company, 
            membership=membership, 
            event_time__range=(start_utc, end_utc)
        ).order_by("event_time")