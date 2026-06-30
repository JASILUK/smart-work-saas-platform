# apps/attendance/selectors/hr_directory_selector.py
import datetime
from django.db.models import Q, F, Case, When, Value, CharField, QuerySet, Prefetch
from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance, DailyAttendanceStatus

class HREmployeeDirectorySelector:
    """
    High-performance selector executing optimized, multi-tenant company isolated 
    database extraction passes for the corporate employee attendance directory.
    """

    @classmethod
    def get_optimized_directory_queryset(
        cls, 
        *, 
        company: Company, 
        target_date: datetime.date
    ) -> QuerySet[Membership]:
        """
        Constructs the baseline Left-Joined Queryset framework between Membership and DailyAttendance.
        Annotates calculated metrics and resolves states at the database layer to prevent N+1 overhead.
        """
        # Prefetch the exact daily attendance record for the specific target date to handle timeline needs
        daily_attendance_prefetch = Prefetch(
            "daily_attendance_records",
            queryset=DailyAttendance.objects.filter(company=company, attendance_date=target_date),
            to_attr="date_attendance_cached"
        )

        # Base active query framework targeting employees, pulling critical relations in one pass
        queryset = Membership.objects.filter(company=company).select_related(
            "user",
            "department",
            "role"
        ).prefetch_related(daily_attendance_prefetch)

        # Annotating the queryset with structural references from the sub-ledger matching the target date
        target_attendance = DailyAttendance.objects.filter(
            company=company,
            membership=OuterRef("pk"),
            attendance_date=target_date
        )

        queryset = queryset.annotate(
            has_record=Exists(target_attendance),
            db_record_id=Subquery(target_attendance.values("id")[:1]),
            db_status=Subquery(target_attendance.values("attendance_status")[:1]),
            db_first_in=Subquery(target_attendance.values("first_check_in_at")[:1]),
            db_last_out=Subquery(target_attendance.values("last_check_out_at")[:1]),
            db_work_min=Subquery(target_attendance.values("total_work_minutes")[:1]),
            db_break_min=Subquery(target_attendance.values("total_break_minutes")[:1]),
            db_late_min=Subquery(target_attendance.values("late_minutes")[:1]),
            db_ot_min=Subquery(target_attendance.values("overtime_minutes")[:1]),
            db_auto_closed=Subquery(target_attendance.values("is_auto_closed")[:1]),
            db_needs_review=Subquery(target_attendance.values("needs_review")[:1]),
            db_review_reason=Subquery(target_attendance.values("review_reason")[:1]),
            db_source=Subquery(target_attendance.values("source")[:1]),
            
            # Extract schedule fields safely out of the JSON structures at the database layer
            db_shift_name=Subquery(target_attendance.values("schedule_snapshot__shift_name")[:1]),
            db_schedule_start=Subquery(target_attendance.values("schedule_snapshot__expected_clock_in")[:1]),
            db_schedule_end=Subquery(target_attendance.values("schedule_snapshot__expected_clock_out")[:1])
        )

        # Compute the explicit "Current State" token algorithm via database Case expressions
        queryset = queryset.annotate(
            computed_current_state=Case(
                When(has_record=False, then=Value("Not Started")),
                When(db_needs_review=True, then=Value("Needs Review")),
                When(db_status=DailyAttendanceStatus.LEAVE, then=Value("On Leave")),
                When(db_status=DailyAttendanceStatus.HOLIDAY, then=Value("Holiday")),
                When(db_status=DailyAttendanceStatus.WEEKEND, then=Value("Weekend")),
                When(db_status=DailyAttendanceStatus.ABSENT, then=Value("Absent")),
                When(db_first_in__isnull=False, db_last_out__isnull=False, then=Value("Checked Out")),
                When(db_first_in__isnull=False, db_last_out__isnull=True, then=Value("Working")),
                default=Value("Not Started"),
                output_field=CharField()
            )
        )

        return queryset

from django.db.models import Exists, Subquery, OuterRef