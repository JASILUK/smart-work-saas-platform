from typing import Dict
from django.utils import timezone
from apps.companies.models import Company, Membership
from apps.attendance.models.attendance_event import AttendanceEventTypes
from apps.attendance.selectors.attendance_event_selector import AttendanceEventSelector


class LiveAttendanceService:
    """
    Evaluates historical daily tracking chains to compute real-time structural presence states.
    """

    @classmethod
    def get_member_status(cls, *, company: Company, membership: Membership) -> str:
        """ Returns: ABSENT, PRESENT, ON_BREAK, CHECKED_OUT. """
        latest = AttendanceEventSelector.get_latest_event(company=company, membership=membership, target_date=timezone.now().date())
        if not latest:
            return "ABSENT"
        if latest.event_type == AttendanceEventTypes.CHECK_OUT:
            return "CHECKED_OUT"
        if latest.event_type == AttendanceEventTypes.BREAK_OUT:
            return "ON_BREAK"
        return "PRESENT"

    @classmethod
    def get_company_summary(cls, *, company: Company) -> Dict[str, int]:
        """ Aggregates operational status counts across the entire workforce. """
        active_staff = company.memberships.filter(is_active=True)
        summary = {"present": 0, "checked_out": 0, "on_break": 0, "absent": 0}
        
        for member in active_staff:
            status_str = cls.get_member_status(company=company, membership=member)
            summary[status_str.lower()] += 1
            
        return summary