# apps/attendance/selectors/attendance_trend_selector.py
"""
Attendance Trend Selector

Compiles chart-ready trend datasets grouped by daily, weekly, and monthly
intervals using optimized database truncations and aggregations.

Also provides status distribution counts and specialized trend lines
for late minutes, work hours, and overtime hours.
"""

import datetime
from typing import Dict, Any, List

from django.db.models import Q, Count, Sum, Avg, F, QuerySet, Value
from django.db.models.functions import TruncWeek, TruncMonth, Coalesce

from apps.companies.models import Company
from apps.attendance.models.daily_attendance import DailyAttendance, DailyAttendanceStatus


class AttendanceTrendSelector:
    """
    Generates trend chart data and status distribution for the profile view.
    """

    # ------------------------------------------------------------------
    # Main Trend Charts
    # ------------------------------------------------------------------

    @classmethod
    def get_trend_charts(
        cls,
        *,
        company: Company,
        membership_id: int,
        start_date: datetime.date,
        end_date: datetime.date
    ) -> Dict[str, Any]:
        """
        Compiles all trend chart datasets in a single structured response.

        Returns:
            dict: Contains daily, weekly, monthly, late_trend, work_hours_trend, overtime_trend.
        """
        base_qs = DailyAttendance.objects.filter(
            company=company,
            membership_id=membership_id,
            attendance_date__range=(start_date, end_date)
        )

        return {
            "daily": cls._get_daily_trends(base_qs),
            "weekly": cls._get_weekly_trends(base_qs),
            "monthly": cls._get_monthly_trends(base_qs),
            "late_trend": cls._get_late_trend(base_qs),
            "work_hours_trend": cls._get_work_hours_trend(base_qs),
            "overtime_trend": cls._get_overtime_trend(base_qs),
        }

    # ------------------------------------------------------------------
    # Daily Trends
    # ------------------------------------------------------------------

    @classmethod
    def _get_daily_trends(cls, base_qs: QuerySet) -> List[Dict[str, Any]]:
        """Daily granular trend data — frontend-ready."""
        return [
            {
                "date": str(item["attendance_date"]),
                "work_hours": round(item["total_work_minutes"] / 60.0, 2) if item["total_work_minutes"] else 0.0,
                "overtime_hours": round(item["overtime_minutes"] / 60.0, 2) if item["overtime_minutes"] else 0.0,
                "late_minutes": item["late_minutes"] or 0,
                "status": item["attendance_status"],
                "is_present": item["is_present"],
                "is_absent": item["is_absent"],
                "is_late": item["is_late"],
                "is_early_exit": item["is_early_exit"],
            }
            for item in base_qs.order_by("attendance_date").values(
                "attendance_date",
                "total_work_minutes",
                "overtime_minutes",
                "late_minutes",
                "attendance_status",
                "is_present",
                "is_absent",
                "is_late",
                "is_early_exit"
            )
        ]

    # ------------------------------------------------------------------
    # Weekly Trends
    # ------------------------------------------------------------------

    @classmethod
    def _get_weekly_trends(cls, base_qs: QuerySet) -> List[Dict[str, Any]]:
        """Weekly aggregated trend data using TruncWeek."""
        weekly_stream = base_qs.annotate(
            week_period=TruncWeek("attendance_date")
        ).values("week_period").annotate(
            total_work=Coalesce(Sum("total_work_minutes"), Value(0)),
            total_ot=Coalesce(Sum("overtime_minutes"), Value(0)),
            total_late=Coalesce(Sum("late_minutes"), Value(0)),
            late_days=Count("id", filter=Q(is_late=True)),
            present_days=Count("id", filter=Q(is_present=True)),
            absent_days=Count("id", filter=Q(is_absent=True)),
            half_days=Count("id", filter=Q(is_half_day=True)),
            working_days=Count("id", filter=~Q(is_holiday=True) & ~Q(is_weekend=True) & ~Q(is_leave=True)),
        ).order_by("week_period")

        return [
            {
                "week_starting": str(item["week_period"]),
                "total_work_hours": round(item["total_work"] / 60.0, 2),
                "total_overtime_hours": round(item["total_ot"] / 60.0, 2),
                "total_late_minutes": item["total_late"],
                "late_days_count": item["late_days"],
                "present_days_count": item["present_days"],
                "absent_days_count": item["absent_days"],
                "half_days_count": item["half_days"],
                "working_days_count": item["working_days"],
            }
            for item in weekly_stream
        ]

    # ------------------------------------------------------------------
    # Monthly Trends
    # ------------------------------------------------------------------

    @classmethod
    def _get_monthly_trends(cls, base_qs: QuerySet) -> List[Dict[str, Any]]:
        """Monthly aggregated trend data using TruncMonth."""
        monthly_stream = base_qs.annotate(
            month_period=TruncMonth("attendance_date")
        ).values("month_period").annotate(
            total_work=Coalesce(Sum("total_work_minutes"), Value(0)),
            total_ot=Coalesce(Sum("overtime_minutes"), Value(0)),
            total_late=Coalesce(Sum("late_minutes"), Value(0)),
            total_break=Coalesce(Sum("total_break_minutes"), Value(0)),
            late_days=Count("id", filter=Q(is_late=True)),
            present_days=Count("id", filter=Q(is_present=True)),
            absent_days=Count("id", filter=Q(is_absent=True)),
            half_days=Count("id", filter=Q(is_half_day=True)),
            leave_days=Count("id", filter=Q(is_leave=True)),
            working_days=Count("id", filter=~Q(is_holiday=True) & ~Q(is_weekend=True) & ~Q(is_leave=True)),
        ).order_by("month_period")

        return [
            {
                "month": str(item["month_period"]),
                "total_work_hours": round(item["total_work"] / 60.0, 2),
                "total_overtime_hours": round(item["total_ot"] / 60.0, 2),
                "total_break_hours": round(item["total_break"] / 60.0, 2),
                "total_late_minutes": item["total_late"],
                "late_days_count": item["late_days"],
                "present_days_count": item["present_days"],
                "absent_days_count": item["absent_days"],
                "half_days_count": item["half_days"],
                "leave_days_count": item["leave_days"],
                "working_days_count": item["working_days"],
            }
            for item in monthly_stream
        ]

    # ------------------------------------------------------------------
    # Specialized Trend Lines
    # ------------------------------------------------------------------

    @classmethod
    def _get_late_trend(cls, base_qs: QuerySet) -> List[Dict[str, Any]]:
        """Late minutes trend by date for line chart rendering."""
        return [
            {
                "date": str(item["attendance_date"]),
                "late_minutes": item["late_minutes"] or 0,
                "late_count": item["late_count"]
            }
            for item in base_qs.filter(is_late=True)
            .order_by("attendance_date")
            .values("attendance_date")
            .annotate(
                late_minutes=Sum("late_minutes"),
                late_count=Count("id")
            )
        ]

    @classmethod
    def _get_work_hours_trend(cls, base_qs: QuerySet) -> List[Dict[str, Any]]:
        """Work hours trend by date for line chart rendering."""
        return [
            {
                "date": str(item["attendance_date"]),
                "work_hours": round((item["work_hours"] or 0) / 60.0, 2),
                "break_hours": round((item["break_hours"] or 0) / 60.0, 2),
            }
            for item in base_qs.order_by("attendance_date")
            .values("attendance_date")
            .annotate(
                work_hours=Sum("total_work_minutes"),
                break_hours=Sum("total_break_minutes")
            )
        ]

    @classmethod
    def _get_overtime_trend(cls, base_qs: QuerySet) -> List[Dict[str, Any]]:
        """Overtime hours trend by date for line chart rendering."""
        return [
            {
                "date": str(item["attendance_date"]),
                "overtime_hours": round((item["overtime_minutes"] or 0) / 60.0, 2),
                "overtime_count": item["overtime_count"]
            }
            for item in base_qs.filter(overtime_minutes__gt=0)
            .order_by("attendance_date")
            .values("attendance_date")
            .annotate(
                overtime_minutes=Sum("overtime_minutes"),
                overtime_count=Count("id")
            )
        ]

    # ------------------------------------------------------------------
    # Status Distribution
    # ------------------------------------------------------------------

    @classmethod
    def get_status_distribution(
        cls,
        *,
        company: Company,
        membership_id: int,
        start_date: datetime.date,
        end_date: datetime.date
    ) -> List[Dict[str, Any]]:
        """
        Returns counts for each attendance status in the period.

        Statuses:
            PRESENT, ABSENT, HALF_DAY, LEAVE, HOLIDAY, WEEKEND, INCOMPLETE, REVIEW_REQUIRED
        """
        base_qs = DailyAttendance.objects.filter(
            company=company,
            membership_id=membership_id,
            attendance_date__range=(start_date, end_date)
        )

        distribution = base_qs.values("attendance_status").annotate(
            count=Count("id")
        ).order_by("attendance_status")

        # Build a complete map with zero defaults for missing statuses
        status_counts = {item["attendance_status"]: item["count"] for item in distribution}
        all_statuses = [
            DailyAttendanceStatus.PRESENT,
            DailyAttendanceStatus.ABSENT,
            DailyAttendanceStatus.HALF_DAY,
            DailyAttendanceStatus.LEAVE,
            DailyAttendanceStatus.HOLIDAY,
            DailyAttendanceStatus.WEEKEND,
            DailyAttendanceStatus.INCOMPLETE,
            DailyAttendanceStatus.REVIEW_REQUIRED,
        ]

        return [
            {
                "status": status,
                "label": DailyAttendanceStatus(status).label,
                "count": status_counts.get(status, 0)
            }
            for status in all_statuses
        ]