# apps/attendance/selectors/attendance_record_selector.py
"""
Attendance Record Selector

Handles optimized sub-ledger data list extraction for an individual employee.
Enforces server-side sorting boundaries, applies all supported filters,
and returns a QuerySet ready for pagination in the view layer.
"""

from typing import Dict, Any

from django.db.models import QuerySet, Q

from apps.companies.models import Company
from apps.attendance.models.daily_attendance import DailyAttendance


class AttendanceRecordSelector:
    """
    Builds filtered, ordered querysets for paginated attendance record lists.
    """

    ALLOWED_SORTING_FIELDS = {
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
        "-attendance_status": "-attendance_status",
        "early_exit": "early_exit_minutes",
        "-early_exit": "-early_exit_minutes",
    }

    @classmethod
    def get_profile_records_queryset(
        cls,
        *,
        company: Company,
        membership_id: int,
        filters: Dict[str, Any]
    ) -> QuerySet[DailyAttendance]:
        """
        Builds a filtered, ordered queryset for single-employee attendance records.

        Args:
            company: The tenant company instance.
            membership_id: The employee membership ID.
            filters: Normalized filter dictionary from the service layer.

        Returns:
            QuerySet[DailyAttendance]: Ordered queryset ready for pagination.
        """
        queryset = DailyAttendance.objects.filter(
            company=company,
            membership_id=membership_id
        ).select_related(
            "company",
            "membership"
        )

        # --- Date Range ---
        if filters.get("start_date") and filters.get("end_date"):
            queryset = queryset.filter(
                attendance_date__range=(filters["start_date"], filters["end_date"])
            )

        # --- Status Filter ---
        if filters.get("attendance_status"):
            queryset = queryset.filter(attendance_status=filters["attendance_status"])

        # --- Boolean Flag Filters ---
        if filters.get("late_only"):
            queryset = queryset.filter(late_minutes__gt=0)

        if filters.get("needs_review"):
            queryset = queryset.filter(needs_review=True)

        if filters.get("auto_closed"):
            queryset = queryset.filter(is_auto_closed=True)

        if filters.get("missing_checkout"):
            queryset = queryset.filter(
                first_check_in_at__isnull=False,
                last_check_out_at__isnull=True,
                is_auto_closed=False,
                needs_review=True
            )

        if filters.get("holiday_only"):
            queryset = queryset.filter(is_holiday=True)

        if filters.get("weekend_only"):
            queryset = queryset.filter(is_weekend=True)

        if filters.get("leave_only"):
            queryset = queryset.filter(is_leave=True)

        # --- Text Search ---
        if filters.get("search_notes"):
            queryset = queryset.filter(review_reason__icontains=filters["search_notes"])

        # --- Server-Side Ordering ---
        sort_param = filters.get("ordering", "-attendance_date")
        db_sort_column = cls.ALLOWED_SORTING_FIELDS.get(sort_param, "-attendance_date")
        queryset = queryset.order_by(db_sort_column)

        return queryset