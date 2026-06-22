import datetime
from typing import Dict
from django.utils import timezone
from apps.companies.models import Company, Membership
from apps.attendance.selectors.attendance_event_selector import AttendanceEventSelector

class LiveAttendanceService:
    """
    Evaluates historical daily tracking chains to compute real-time structural presence states.
    """

    @classmethod
    def get_member_status(cls, *, company: Company, membership: Membership) -> str:
        """
        Returns: ABSENT, PRESENT, ON_BREAK, CHECKED_OUT.
        Default evaluation defaults to current local server date configurations.
        """
        today_local = timezone.localtime(timezone.now()).date()
        return cls.get_member_status_for_date(membership=membership, date=today_local)

    @classmethod
    def get_member_status_for_date(cls, *, membership: Membership, date: datetime.date) -> str:
        """
        Synthesized entry point matching dashboard telemetry aggregation contracts securely.
        Accepts explicit date parameters to evaluate historical status without timezone offset drift.
        Maps internal system event types to exact dashboard orchestration status states:
        - CHECK_IN -> CHECKED_IN
        - BREAK_OUT -> ON_BREAK
        - BREAK_IN -> CHECKED_IN
        - CHECK_OUT -> CHECKED_OUT
        - No Events -> NOT_CHECKED_IN
        """
        latest = AttendanceEventSelector.get_latest_event(
            company=membership.company, 
            membership=membership, 
            target_date=date
        )
        
        if not latest:
            return "NOT_CHECKED_IN"
            
        event_type = getattr(latest, 'event_type', None)
        
        if event_type == 'CHECK_OUT':
            return "CHECKED_OUT"
        if event_type == 'BREAK_OUT':
            return "ON_BREAK"
        if event_type in ['CHECK_IN', 'BREAK_IN']:
            return "CHECKED_IN"
            
        return "NOT_CHECKED_IN"

    @classmethod
    def get_company_summary(cls, *, company: Company) -> Dict[str, int]:
        """ Aggregates operational status counts across the entire workforce. """
        active_staff = company.memberships.filter(is_active=True)
        summary = {"present": 0, "checked_out": 0, "on_break": 0, "absent": 0}
        
        for member in active_staff:
            status_str = cls.get_member_status(company=company, membership=member)
            # Support conversion matching payload structures
            key = status_str.lower()
            if key == "checked_in":
                key = "present"
            elif key == "not_checked_in":
                key = "absent"
                
            if key in summary:
                summary[key] += 1
            
        return summary