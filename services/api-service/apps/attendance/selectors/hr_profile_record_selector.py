from django.db.models import QuerySet, Q
from apps.companies.models import Company
from apps.attendance.models.daily_attendance import DailyAttendance

class HRProfileRecordSelector:
    """
    Handles optimized sub-ledger data list extraction grids for an individual employee.
    Enforces server-side ordering fields to keep processing overhead low.
    """

    ALLOWED_SORTING_DICTS = {
        "attendance_date": "attendance_date",
        "-attendance_date": "-attendance_date",
        "check_in": "first_check_in_at",
        "-check_in": "-first_check_in_at",
        "check_out": "last_check_out_at",
        "-check_out": "-last_check_out_at",
        "late_minutes": "late_minutes",
        "-late_minutes": "-late_minutes",
        "work_hours": "total_work_minutes",
        "-work_hours": "-total_work_minutes",
        "overtime": "overtime_minutes",
        "-overtime": "-overtime_minutes",
        "attendance_status": "attendance_status",
        "-attendance_status": "-attendance_status"
    }

    @classmethod
    def get_profile_records_queryset(cls, *, company: Company, membership_id: int, filters: dict) -> QuerySet[DailyAttendance]:
        """
        Builds a filtered query statement matching single-employee timeline requests.
        """
        queryset = DailyAttendance.objects.filter(company=company, membership_id=membership_id)

        # Apply structural range constraints
        if filters.get("start_date") and filters.get("end_date"):
            queryset = queryset.filter(attendance_date__range=(filters["start_date"], filters["end_date"]))

        if filters.get("attendance_status"):
            queryset = queryset.filter(attendance_status=filters["attendance_status"])

        if filters.get("late_only"):
            queryset = queryset.filter(late_minutes__gt=0)

        if filters.get("needs_review"):
            queryset = queryset.filter(needs_review=True)

        if filters.get("auto_closed"):
            queryset = queryset.filter(is_auto_closed=True)

        if filters.get("search_notes"):
            queryset = queryset.filter(review_reason__icontains=filters["search_notes"])

        # Enforce server-side sorting boundaries cleanly
        sort_param = filters.get("ordering", "-attendance_date")
        db_sort_column = cls.ALLOWED_SORTING_DICTS.get(sort_param, "-attendance_date")
        
        return queryset.order_by(db_sort_column)