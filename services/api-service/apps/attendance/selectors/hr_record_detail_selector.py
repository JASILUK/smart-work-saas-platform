# apps/attendance/selectors/hr_record_detail_selector.py
from typing import Optional, Tuple, List
import datetime
from apps.companies.models import Company
from apps.attendance.models.daily_attendance import DailyAttendance
from apps.attendance.models.attendance_event import AttendanceEvent
from apps.attendance.models.employee_attendance_override import EmployeeAttendanceOverride

# Import your shift-aware event selector
from apps.attendance.selectors.attendance_event_selector import AttendanceEventSelector


class HRRecordDetailSelector:
    """
    High-performance selector layer isolating a single DailyAttendance ledger sheet.
    Prefetches structural tracking streams and historical modifications to eliminate N+1 loops.
    """

    @classmethod
    def get_comprehensive_record_graph(
        cls, *, company: Company, record_id: int
    ) -> Optional[Tuple[DailyAttendance, List[AttendanceEvent], List[EmployeeAttendanceOverride]]]:
        """
        Loads the core record using select_related, and performs isolated indexed lookups 
        to capture events and corporate audit logs efficiently.
        """
        # 1. Fetch the primary DailyAttendance record row using pre-optimized joins
        record = DailyAttendance.objects.select_related(
            "membership",
            "membership__user",
            "membership__department",
            "finalized_by",
            "finalized_by__user"
        ).filter(id=record_id, company=company).first()

        if not record:
            return None

        # 2. ✅ FIXED: Delegate event extraction to your schedule-aware AttendanceEventSelector
        # This automatically resolves night-shift boundaries using the employee's rules.
        events = list(
            AttendanceEventSelector.get_events_for_membership_and_date(
                membership=record.membership,
                date=record.attendance_date
            ).select_related(
                "location", 
                "created_by__user"
            ).order_by("event_time")
        )

        # 3. Fetch matching administrative adjustments using employee membership targets
        audit_history = list(
            EmployeeAttendanceOverride.objects.filter(
                company=company,
                membership=record.membership
            ).select_related(
                "override_by__user" if hasattr(EmployeeAttendanceOverride, "override_by") else "company"
            ).order_by("-created_at")
        )

        return record, events, audit_history