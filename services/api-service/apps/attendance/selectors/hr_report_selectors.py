# apps/attendance/selectors/hr_report_selectors.py
import datetime
from typing import Dict, Any, Optional
from django.db.models import QuerySet, Q, Count, Avg, Sum, F, fields
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from apps.companies.models import Company
from apps.attendance.models.daily_attendance import DailyAttendance, DailyAttendanceStatus

class HRReportDataSelector:
    """
    Executes high-density historical aggregations, payroll timesheet summaries,
    and rolling multi-week trend lines across large tenant groups.
    """

    @classmethod
    def apply_unified_filter_matrix(cls, queryset: QuerySet, filters: Dict[str, Any]) -> QuerySet:
        """
        Applies standard filter criteria safely to historical data lookups.
        """
        if filters.get("date_from"):
            queryset = queryset.filter(attendance_date__gte=filters["date_from"])
        if filters.get("date_to"):
            queryset = queryset.filter(attendance_date__lte=filters["date_to"])
        if filters.get("department_id"):
            queryset = queryset.filter(membership__department_id=filters["department_id"])
        if filters.get("membership_id"):
            queryset = queryset.filter(membership_id=filters["membership_id"])
        if filters.get("status"):
            queryset = queryset.filter(attendance_status=filters["status"])
        if filters.get("needs_review") is not None:
            queryset = queryset.filter(needs_review=filters["needs_review"])
        if filters.get("is_auto_closed") is not None:
            queryset = queryset.filter(is_auto_closed=filters["is_auto_closed"])
        if filters.get("late_only"):
            queryset = queryset.filter(is_late=True)
        if filters.get("early_exit_only"):
            queryset = queryset.filter(is_early_exit=True)
        if filters.get("overtime_only"):
            queryset = queryset.filter(overtime_minutes__gt=0)
            
        if filters.get("search"):
            search_val = filters["search"]
            queryset = queryset.filter(
                Q(membership__user__first_name__icontains=search_val) |
                Q(membership__user__last_name__icontains=search_val) |
                Q(membership__user__email__icontains=search_val)
            )
        return queryset

    @classmethod
    def get_historical_summary_metrics(cls, *, company: Company, filters: Dict[str, Any]) -> dict:
        """
        Computes high-level period KPIs in a single database pass.
        """
        base_qs = DailyAttendance.objects.filter(company=company)
        base_qs = cls.apply_unified_filter_matrix(base_qs, filters)

        aggregations = base_qs.aggregate(
            total_records=Count("id"),
            present=Count("id", filter=Q(is_present=True)),
            absent=Count("id", filter=Q(is_absent=True)),
            half_day=Count("id", filter=Q(is_half_day=True)),
            late=Count("id", filter=Q(is_late=True)),
            leave=Count("id", filter=Q(is_leave=True)),
            holiday=Count("id", filter=Q(is_holiday=True)),
            weekend=Count("id", filter=Q(is_weekend=True)),
            review=Count("id", filter=Q(needs_review=True)),
            auto_closed=Count("id", filter=Q(is_auto_closed=True)),
            
            sum_work_min=Sum("total_work_minutes"),
            sum_break_min=Sum("total_break_minutes"),
            sum_late_min=Sum("late_minutes"),
            sum_ot_min=Sum("overtime_minutes"),
            
            avg_work_min=Avg("total_work_minutes"),
            avg_break_min=Avg("total_break_minutes"),
            avg_in=Avg(F("first_check_in_at") - F("first_check_in_at__date")),
            avg_out=Avg(F("last_check_out_at") - F("last_check_out_at__date"))
        )

        total = aggregations["total_records"] or 0
        present = aggregations["present"] or 0
        working_days = present + (aggregations["absent"] or 0) + (aggregations["half_day"] or 0)
        attendance_pct = (present / working_days * 100.0) if working_days > 0 else 0.0

        def _format_avg_time(delta) -> str:
            if not delta: return "--:--"
            secs = int(delta.total_seconds())
            return f"{(secs // 3600) % 24:02d}:{(secs // 60) % 60:02d}"

        return {
            "total_attendance_records": total,
            "present": present,
            "absent": aggregations["absent"] or 0,
            "late": aggregations["late"] or 0,
            "half_day": aggregations["half_day"] or 0,
            "leave": aggregations["leave"] or 0,
            "holiday": aggregations["holiday"] or 0,
            "weekend": aggregations["weekend"] or 0,
            "attendance_percentage": round(attendance_pct, 2),
            "average_working_hours": round((aggregations["avg_work_min"] or 0) / 60.0, 2),
            "average_break_hours": round((aggregations["avg_break_min"] or 0) / 60.0, 2),
            "average_check_in": _format_avg_time(aggregations["avg_in"]),
            "average_check_out": _format_avg_time(aggregations["avg_out"]),
            "average_late_minutes": round(aggregations["sum_late_min"] / total, 2) if total > 0 and aggregations["sum_late_min"] else 0.0,
            "average_overtime": round((aggregations["sum_ot_min"] or 0) / 60.0 / total, 2) if total > 0 and aggregations["sum_ot_min"] else 0.0,
            "needs_review_count": aggregations["review"] or 0,
            "auto_closed_count": aggregations["auto_closed"] or 0
        }

    @classmethod
    def get_payroll_dataset(cls, *, company: Company, filters: Dict[str, Any]) -> QuerySet:
        """
        Compiles a high-performance payroll summary grouped by employee membership.
        """
        base_qs = DailyAttendance.objects.filter(company=company)
        base_qs = cls.apply_unified_filter_matrix(base_qs, filters)

        # Optimization Pass: Calculate employee metrics using high-speed database aggregations
        return base_qs.values(
            "membership_id",
            "membership__user__first_name",
            "membership__user__last_name",
            "membership__user__username",
            "membership__department__name"
        ).annotate(
            scheduled_days=Count("id"),
            present_days=Count("id", filter=Q(is_present=True)),
            absent_days=Count("id", filter=Q(is_absent=True)),
            leave_days=Count("id", filter=Q(is_leave=True)),
            late_days=Count("id", filter=Q(is_late=True)),
            half_days=Count("id", filter=Q(is_half_day=True)),
            weekend_count=Count("id", filter=Q(is_weekend=True)),
            holiday_count=Count("id", filter=Q(is_holiday=True)),
            total_work_minutes_sum=Sum("total_work_minutes"),
            total_overtime_minutes_sum=Sum("overtime_minutes")
        ).order_by("membership__user__first_name")

    @classmethod
    def get_analytics_trends(cls, *, company: Company, filters: Dict[str, Any]) -> dict:
        """
        Generates chart-ready historical trend datasets using database truncations.
        """
        base_qs = DailyAttendance.objects.filter(company=company)
        base_qs = cls.apply_unified_filter_matrix(base_qs, filters)

        # 1. Daily Trend metrics stream
        daily_stream = base_qs.annotate(
            period=TruncDate("attendance_date")
        ).values("period").annotate(
            present=Count("id", filter=Q(is_present=True)),
            late=Count("id", filter=Q(is_late=True)),
            hours=Sum("total_work_minutes")
        ).order_by("period")

        # 2. Functional Distribution percentages pass
        status_distribution = base_qs.values("attendance_status").annotate(count=Count("id"))
        method_distribution = base_qs.values("source").annotate(count=Count("id"))

        return {
            "daily_trend": [
                {
                    "date": str(item["period"]),
                    "present_count": item["present"],
                    "late_count": item["late"],
                    "total_work_hours": round((item["hours"] or 0) / 60.0, 2)
                } for item in daily_stream
            ],
            "status_distribution": [
                {"status": item["attendance_status"], "count": item["count"]} for item in status_distribution
            ],
            "method_distribution": [
                {"method": item["source"], "count": item["count"]} for item in method_distribution
            ]
        }