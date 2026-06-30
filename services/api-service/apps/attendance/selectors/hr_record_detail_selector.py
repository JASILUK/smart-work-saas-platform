# apps/attendance/selectors/hr_record_detail_selector.py
from typing import Optional, Tuple, List
from django.db.models import QuerySet
from apps.companies.models import Company
from apps.attendance.models.daily_attendance import DailyAttendance
from apps.attendance.models.attendance_event import AttendanceEvent
from apps.attendance.models.employee_attendance_override import EmployeeAttendanceOverride

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

        # 2. Fetch the corresponding event history using composite indexes
        events = list(
            AttendanceEvent.objects.filter(
                company=company,
                membership=record.membership,
                event_time__date=record.attendance_date
            ).select_related(
                "location", 
                "created_by__user"
            ).order_by("event_time")
        )

        # 3. Fetch matching administrative adjustments using foreign key targets
        audit_history = list(
            EmployeeAttendanceOverride.objects.filter(
                company=company,
                daily_attendance=record
            ).select_related(
                "override_by__user"
            ).order_by("-created_at")
        )

        return record, events, audit_history