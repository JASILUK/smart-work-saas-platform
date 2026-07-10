# apps/attendance/selectors/attendance_summary_selector.py
"""
Attendance Summary Selector

Computes aggregated performance counters, duration averages, and period-level
KPIs at the database level for an individual employee workspace history.

All calculations are pushed to PostgreSQL via aggregate() and annotate()
to eliminate Python-side iteration.
"""

import datetime
from typing import Dict, Any

from django.db import models
from django.db.models import Q, Count, Avg, Sum, F, Value, Func
from django.db.models.functions import Coalesce

from apps.companies.models import Company
from apps.attendance.models.daily_attendance import DailyAttendance


# ------------------------------------------------------------------------------
# PostgreSQL-native EXTRACT(EPOCH FROM ...) wrapper
# Works across ALL Django versions since it uses raw SQL function template
# ------------------------------------------------------------------------------
class ExtractEpoch(Func):
    """
    Custom ORM function that maps to PostgreSQL's EXTRACT(EPOCH FROM column).

    Returns the number of seconds since the Unix epoch (1970-01-01 00:00:00 UTC).
    When applied to a timestamp minus its date portion, yields seconds-since-midnight.
    """
    function = "EXTRACT"
    template = "%(function)s(EPOCH FROM %(expressions)s)"
    output_field = models.FloatField()


class AttendanceSummarySelector:
    """
    Computes summary KPIs for the employee attendance profile.
    """

    @classmethod
    def get_period_summary(
        cls,
        *,
        company: Company,
        membership_id: int,
        start_date: datetime.date,
        end_date: datetime.date
    ) -> Dict[str, Any]:
        """
        Executes a single optimized aggregation query for all summary KPIs.

        Working Day Rule:
            Working Days = Calendar Days - Holiday - Weekend - Approved Leave

        Attendance Percentage:
            Attendance % = Present / Working Days
        """
        base_qs = DailyAttendance.objects.filter(
            company=company,
            membership_id=membership_id,
            attendance_date__range=(start_date, end_date)
        )

        # Single-query aggregation for all counters and durations
        aggregations = base_qs.aggregate(
            calendar_days=Count("id"),
            present_days=Count("id", filter=Q(is_present=True)),
            absent_days=Count("id", filter=Q(is_absent=True)),
            half_days=Count("id", filter=Q(is_half_day=True)),
            late_days=Count("id", filter=Q(is_late=True)),
            early_exit_days=Count("id", filter=Q(is_early_exit=True)),
            leave_days=Count("id", filter=Q(is_leave=True)),
            holiday_days=Count("id", filter=Q(is_holiday=True)),
            weekend_days=Count("id", filter=Q(is_weekend=True)),
            needs_review_count=Count("id", filter=Q(needs_review=True)),
            missing_checkout_count=Count(
                "id",
                filter=Q(
                    first_check_in_at__isnull=False,
                    last_check_out_at__isnull=True,
                    is_auto_closed=False,
                    needs_review=True
                )
            ),
            auto_closed_count=Count("id", filter=Q(is_auto_closed=True)),
            # Duration sums
            sum_work_min=Coalesce(Sum("total_work_minutes"), Value(0)),
            sum_break_min=Coalesce(Sum("total_break_minutes"), Value(0)),
            sum_ot_min=Coalesce(Sum("overtime_minutes"), Value(0)),
            sum_late_min=Coalesce(Sum("late_minutes"), Value(0)),
            # Duration averages
            avg_work_min=Avg("total_work_minutes"),
            avg_break_min=Avg("total_break_minutes"),
            # Time-punch averages using PostgreSQL EXTRACT(EPOCH FROM ...)
            # Subtracting date portion gives seconds-since-midnight for each record
            avg_in_seconds=Avg(
                ExtractEpoch(F("first_check_in_at")) - ExtractEpoch(F("first_check_in_at__date"))
            ),
            avg_out_seconds=Avg(
                ExtractEpoch(F("last_check_out_at")) - ExtractEpoch(F("last_check_out_at__date"))
            ),
        )

        # Extract values with safe defaults
        calendar_days = aggregations["calendar_days"] or 0
        present = aggregations["present_days"] or 0
        absent = aggregations["absent_days"] or 0
        half = aggregations["half_days"] or 0
        holiday = aggregations["holiday_days"] or 0
        weekend = aggregations["weekend_days"] or 0
        leave = aggregations["leave_days"] or 0

        # Working Days = Calendar Days - Holiday - Weekend - Leave
        working_days = calendar_days - holiday - weekend - leave
        if working_days < 0:
            working_days = 0

        # Attendance % = Present / Working Days
        attendance_pct = (present / working_days * 100.0) if working_days > 0 else 0.0

        # Format average time punches from epoch seconds
        avg_check_in = cls._format_avg_time_from_seconds(aggregations["avg_in_seconds"])
        avg_check_out = cls._format_avg_time_from_seconds(aggregations["avg_out_seconds"])

        return {
            # Day counters
            "calendar_days": calendar_days,
            "working_days": working_days,
            "present_days": present,
            "absent_days": absent,
            "half_days": half,
            "late_days": aggregations["late_days"] or 0,
            "early_exit_days": aggregations["early_exit_days"] or 0,
            "leave_days": leave,
            "holiday_days": holiday,
            "weekend_days": weekend,
            # Exception counters
            "needs_review": aggregations["needs_review_count"] or 0,
            "missing_checkout": aggregations["missing_checkout_count"] or 0,
            "auto_closed": aggregations["auto_closed_count"] or 0,
            # Percentage
            "attendance_percentage": round(attendance_pct, 2),
            # Average times
            "average_check_in": avg_check_in,
            "average_check_out": avg_check_out,
            "average_work_hours": round((aggregations["avg_work_min"] or 0) / 60.0, 2),
            "average_break_hours": round((aggregations["avg_break_min"] or 0) / 60.0, 2),
            # Totals
            "total_work_hours": round(aggregations["sum_work_min"] / 60.0, 2),
            "total_break_hours": round(aggregations["sum_break_min"] / 60.0, 2),
            "total_overtime_hours": round(aggregations["sum_ot_min"] / 60.0, 2),
            "late_minutes": aggregations["sum_late_min"],
            "overtime_minutes": aggregations["sum_ot_min"],
        }

    @classmethod
    def _format_avg_time_from_seconds(cls, avg_seconds) -> str:
        """
        Formats average seconds-since-midnight into HH:MM string.

        ExtractEpoch(datetime) - ExtractEpoch(datetime::date) gives seconds since midnight
        for that particular datetime. Averaging those gives the average time-of-day.
        """
        if avg_seconds is None:
            return "--:--"
        total_seconds = int(avg_seconds)
        hours = (total_seconds // 3600) % 24
        minutes = (total_seconds // 60) % 60
        return f"{hours:02d}:{minutes:02d}"