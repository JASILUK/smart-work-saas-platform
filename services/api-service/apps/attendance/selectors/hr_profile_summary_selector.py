import datetime
from django.db.models import Q, Count, Avg, Sum, F, QuerySet
from django.db.models.functions import TruncWeek, TruncMonth
from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance, DailyAttendanceStatus

class HREmployeeSummarySelector:
    """
    Computes aggregated performance counters, duration averages, and historical 
    interval trend lines at the database level for an individual employee workspace history.
    """

    @classmethod
    def get_period_summary_cards(
        cls, *, company: Company, membership_id: int, start_date: datetime.date, end_date: datetime.date
    ) -> dict:
        """
        Executes period aggregations and duration averages for summary cards in a single database query.
        """
        base_qs = DailyAttendance.objects.filter(
            company=company,
            membership_id=membership_id,
            attendance_date__range=(start_date, end_date)
        )

        aggregations = base_qs.aggregate(
            total_days=Count("id"),
            present=Count("id", filter=Q(is_present=True)),
            absent=Count("id", filter=Q(is_absent=True)),
            leave=Count("id", filter=Q(is_leave=True)),
            holiday=Count("id", filter=Q(is_holiday=True)),
            weekend=Count("id", filter=Q(is_weekend=True)),
            late_days=Count("id", filter=Q(is_late=True)),
            half_days=Count("id", filter=Q(is_half_day=True)),
            early_exits=Count("id", filter=Q(is_early_exit=True)),
            auto_closed=Count("id", filter=Q(is_auto_closed=True)),
            
            # FIXED: Renamed output alias from 'needs_review' to 'needs_review_count' to resolve FieldError
            needs_review_count=Count("id", filter=Q(needs_review=True)),
            
            # Duration Sums (Stored inside schema ledger as integer minutes)
            sum_work_min=Sum("total_work_minutes"),
            sum_ot_min=Sum("overtime_minutes"),
            
            # Duration Averages
            avg_work_min=Avg("total_work_minutes"),
            avg_break_min=Avg("total_break_minutes"),
            
            # Time-punch averages extracted from timestamps
            avg_in=Avg(F("first_check_in_at") - F("first_check_in_at__date")),
            avg_out=Avg(F("last_check_out_at") - F("last_check_out_at__date")),
            
            missing_checkout=Count(
                "id",
                filter=Q(first_check_in_at__isnull=False, last_check_out_at__isnull=True, is_auto_closed=False, needs_review=True)
            )
        )

        total_days = aggregations["total_days"] or 0
        present = aggregations["present"] or 0
        leaves = aggregations["leave"] or 0
        
        working_days = present + (aggregations["absent"] or 0) + (aggregations["half_days"] or 0)
        attendance_pct = (present / working_days * 100.0) if working_days > 0 else 0.0

        # Helper string format closures for time deltas
        def _format_avg_time(delta) -> str:
            if not delta:
                return "--:--"
            total_seconds = int(delta.total_seconds())
            hours = (total_seconds // 3600) % 24
            minutes = (total_seconds // 60) % 60
            return f"{hours:02d}:{minutes:02d}"

        return {
            "working_days": working_days,
            "present": present,
            "absent": aggregations["absent"] or 0,
            "leave": leaves,
            "holiday": aggregations["holiday"] or 0,
            "weekend": aggregations["weekend"] or 0,
            "late_days": aggregations["late_days"] or 0,
            "half_days": aggregations["half_days"] or 0,
            "attendance_percentage": round(attendance_pct, 2),
            "average_check_in": _format_avg_time(aggregations["avg_in"]),
            "average_check_out": _format_avg_time(aggregations["avg_out"]),
            "average_work_hours": round((aggregations["avg_work_min"] or 0) / 60.0, 2),
            "average_break_hours": round((aggregations["avg_break_min"] or 0) / 60.0, 2),
            "total_work_hours": round((aggregations["sum_work_min"] or 0) / 60.0, 2),
            "total_overtime": round((aggregations["sum_ot_min"] or 0) / 60.0, 2),
            "early_exits": aggregations["early_exits"] or 0,
            "missing_checkouts": aggregations["missing_checkout"] or 0,
            
            # FIXED: Read from the updated count key name here
            "needs_review": aggregations["needs_review_count"] or 0
        }

    @classmethod
    def get_trend_chart_matrices(
        cls, *, company: Company, membership_id: int, start_date: datetime.date, end_date: datetime.date
    ) -> dict:
        """
        Compiles chart-ready timelines grouped by weekly and monthly intervals 
        using optimized query database truncations.
        """
        base_qs = DailyAttendance.objects.filter(
            company=company, membership_id=membership_id, attendance_date__range=(start_date, end_date)
        )

        # 1. Daily Performance Line Stream
        daily_stream = base_qs.order_by("attendance_date").values(
            "attendance_date", "total_work_minutes", "overtime_minutes", "late_minutes", "attendance_status"
        )
        
        daily_chart = [
            {
                "date": str(item["attendance_date"]),
                "work_hours": round(item["total_work_minutes"] / 60.0, 2),
                "overtime_hours": round(item["overtime_minutes"] / 60.0, 2),
                "late_minutes": item["late_minutes"],
                "status": item["attendance_status"]
            }
            for item in daily_stream
        ]

        # 2. Weekly Truncation Summary Aggregation
        weekly_stream = base_qs.annotate(
            week_period=TruncWeek("attendance_date")
        ).values("week_period").annotate(
            total_work=Sum("total_work_minutes"),
            total_ot=Sum("overtime_minutes"),
            late_days=Count("id", filter=Q(is_late=True)),
            present_days=Count("id", filter=Q(is_present=True))
        ).order_by("week_period")

        weekly_chart = [
            {
                "week_starting": str(item["week_period"]),
                "total_work_hours": round((item["total_work"] or 0) / 60.0, 2),
                "total_overtime_hours": round((item["total_ot"] or 0) / 60.0, 2),
                "late_days_count": item["late_days"],
                "present_days_count": item["present_days"]
            }
            for item in weekly_stream
        ]

        return {
            "daily_trends": daily_chart,
            "weekly_trends": weekly_chart
        }