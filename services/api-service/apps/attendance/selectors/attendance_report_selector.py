# apps/attendance/selectors/attendance_report_selector.py
"""
Attendance Report Selector

Handles enterprise-level PostgreSQL optimizations for the employee-centric
attendance summary metrics report. Consolidates multi-tenant record sets via 
advanced database aggregation and annotation filters.
"""

import datetime
from typing import Dict, Any, Tuple
from django.db import models
from django.db.models import Q, Count, Sum, Avg, Value, FloatField, F
from django.db.models.functions import Coalesce, Cast
from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance, DailyAttendanceStatus


class AttendanceReportSelector:
    """
    Executes database-level optimizations for the enterprise Attendance Reports module.
    """

    @classmethod
    def get_report_data(
        cls,
        *,
        company: Company,
        filters: Dict[str, Any],
        ordering: str
    ) -> Tuple[models.QuerySet, Dict[str, Any]]:
        """
        Builds, filters, and generates aggregations for the employee dataset.
        Returns a tuple of (annotated_membership_queryset, summary_cards_dict).
        """
        date_from = filters["date_from"]
        date_to = filters["date_to"]

        # ----------------------------------------------------------------------
        # 1. Base Employee (Membership) Queryset with structural pre-fetches
        # ----------------------------------------------------------------------
        employee_qs = Membership.objects.select_related(
            "user", "department"
        ).filter(
            company=company,
            is_active=True
        )

        # ----------------------------------------------------------------------
        # 2. Dynamic Structural Query Filtering
        # ----------------------------------------------------------------------
        if filters.get("department_id"):
            employee_qs = employee_qs.filter(department_id=filters["department_id"])
        
        if filters.get("membership_id"):
            employee_qs = employee_qs.filter(id=filters["membership_id"])

        if filters.get("search"):
            search_term = filters["search"].strip()
            employee_qs = employee_qs.filter(
                Q(user__first_name__icontains=search_term) |
                Q(user__last_name__icontains=search_term) |
                Q(user__username__icontains=search_term) |
                Q(job_title__icontains=search_term)
            )

        # Conditional lookup arrays for downstream subquery-filtering constraints
        attendance_filter = Q(daily_attendance_records__attendance_date__range=(date_from, date_to))

        if filters.get("attendance_status"):
            # Filter rows where the employee has at least one record matching the status in that period
            status_filter = Q(
                daily_attendance_records__attendance_date__range=(date_from, date_to),
                daily_attendance_records__attendance_status=filters["attendance_status"]
            )
            employee_qs = employee_qs.filter(status_filter)

        # ----------------------------------------------------------------------
        # 3. PostgreSQL Database Annotations per Employee
        # ----------------------------------------------------------------------
        annotated_queryset = employee_qs.annotate(
            present_days=Count(
                "daily_attendance_records__id",
                filter=attendance_filter & Q(daily_attendance_records__attendance_status=DailyAttendanceStatus.PRESENT)
            ),
            absent_days=Count(
                "daily_attendance_records__id",
                filter=attendance_filter & Q(daily_attendance_records__attendance_status=DailyAttendanceStatus.ABSENT)
            ),
            leave_days=Count(
                "daily_attendance_records__id",
                filter=attendance_filter & Q(daily_attendance_records__attendance_status=DailyAttendanceStatus.LEAVE)
            ),
            holiday_days=Count(
                "daily_attendance_records__id",
                filter=attendance_filter & Q(daily_attendance_records__attendance_status=DailyAttendanceStatus.HOLIDAY)
            ),
            weekend_days=Count(
                "daily_attendance_records__id",
                filter=attendance_filter & Q(daily_attendance_records__attendance_status=DailyAttendanceStatus.WEEKEND)
            ),
            late_count=Count(
                "daily_attendance_records__id",
                filter=attendance_filter & Q(daily_attendance_records__is_late=True)
            ),
            needs_review_count=Count(
                "daily_attendance_records__id",
                filter=attendance_filter & Q(daily_attendance_records__needs_review=True)
            ),
            total_work_minutes_sum=Coalesce(
                Sum("daily_attendance_records__total_work_minutes", filter=attendance_filter), 0
            ),
            total_overtime_minutes_sum=Coalesce(
                Sum("daily_attendance_records__overtime_minutes", filter=attendance_filter), 0
            )
        ).annotate(
            # Working Days = Present + Absent
            working_days_calc=F("present_days") + F("absent_days")
        ).annotate(
            # Calculate metrics properties safely
            attendance_percentage=models.Case(
                models.When(working_days_calc__gt=0, then=Round2Decimal((Cast(F("present_days"), FloatField()) / Cast(F("working_days_calc"), FloatField())) * 100.0)),
                default=Value(0.0),
                output_field=FloatField()
            ),
            total_work_hours=Round2Decimal(Cast(F("total_work_minutes_sum"), FloatField()) / 60.0),
            overtime_hours=Round2Decimal(Cast(F("total_overtime_minutes_sum"), FloatField()) / 60.0),
            needs_review=models.Case(
                models.When(needs_review_count__gt=0, then=Value(True)),
                default=Value(False),
                output_field=models.BooleanField()
            )
        )

        # Apply enterprise-safe dynamic ordering parameters
        annotated_queryset = annotated_queryset.order_by(ordering)

        # ----------------------------------------------------------------------
        # 4. Global Summary Metrics Aggregation Block
        # ----------------------------------------------------------------------
        summary_base_qs = DailyAttendance.objects.filter(
            company=company,
            attendance_date__range=(date_from, date_to)
        )

        # Apply overlapping workforce constraints onto global summary pools
        if filters.get("department_id"):
            summary_base_qs = summary_base_qs.filter(membership__department_id=filters["department_id"])
        if filters.get("membership_id"):
            summary_base_qs = summary_base_qs.filter(membership_id=filters["membership_id"])
        if filters.get("search"):
            search_term = filters["search"].strip()
            summary_base_qs = summary_base_qs.filter(
                Q(membership__user__first_name__icontains=search_term) |
                Q(membership__user__last_name__icontains=search_term) |
                Q(membership__job_title__icontains=search_term)
            )

        summary_metrics = summary_base_qs.aggregate(
            total_present=Count("id", filter=Q(attendance_status=DailyAttendanceStatus.PRESENT)),
            total_absent=Count("id", filter=Q(attendance_status=DailyAttendanceStatus.ABSENT)),
            total_leave=Count("id", filter=Q(attendance_status=DailyAttendanceStatus.LEAVE)),
            total_late=Count("id", filter=Q(is_late=True)),
            sum_work_min=Coalesce(Sum("total_work_minutes"), 0),
            sum_ot_min=Coalesce(Sum("overtime_minutes"), 0)
        )

        total_employees = employee_qs.count()
        total_present_records = summary_metrics["total_present"] or 0
        total_absent_records = summary_metrics["total_absent"] or 0
        total_working_records = total_present_records + total_absent_records

        avg_attendance_pct = 0.0
        if total_working_records > 0:
            avg_attendance_pct = round((total_present_records / total_working_records) * 100.0, 2)

        summary_cards = {
            "total_employees": total_employees,
            "present_employees": total_present_records,
            "absent_employees": total_absent_records,
            "employees_on_leave": summary_metrics["total_leave"] or 0,
            "employees_late": summary_metrics["total_late"] or 0,
            "average_attendance_percentage": avg_attendance_pct,
            "total_work_hours": round(summary_metrics["sum_work_min"] / 60.0, 2),
            "total_overtime_hours": round(summary_metrics["sum_ot_min"] / 60.0, 2)
        }

        return annotated_queryset, summary_cards


class Round2Decimal(models.Func):
    """ Postgre-native function configuration to force absolute rounding parameters """
    function = "ROUND"
    template = "%(function)s(%(expressions)s::numeric, 2)"