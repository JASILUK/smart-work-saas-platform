import datetime
from django.db.models import Q, Count, QuerySet, F
from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance, DailyAttendanceStatus

class HRDashboardSelector:
    """
    Executes high-performance database-level aggregations and annotations 
    for the enterprise HR dashboard, ensuring multi-tenant data isolation.
    """

    @classmethod
    def get_todays_overview_stats(cls, *, company: Company, target_date: datetime.date) -> dict:
        """
        Computes all top-level KPI summary cards in a single database aggregation pass.
        """
        # Calculate total active employee headcount safely from the core membership tables
        total_active_employees = Membership.objects.filter(
            company=company, 
            is_active=True
        ).count()

        aggregations = DailyAttendance.objects.filter(
            company=company, 
            attendance_date=target_date
        ).aggregate(
            present_count=Count("id", filter=Q(is_present=True)),
            absent_count=Count("id", filter=Q(is_absent=True)),
            half_day_count=Count("id", filter=Q(is_half_day=True)),
            late_count=Count("id", filter=Q(is_late=True)),
            leave_count=Count("id", filter=Q(is_leave=True)),
            early_exit_count=Count("id", filter=Q(is_early_exit=True)),
            auto_closed_count=Count("id", filter=Q(is_auto_closed=True)),
            review_required_count=Count("id", filter=Q(needs_review=True)),
            
            # Currently working checks: checked in today but has not checked out yet
            currently_working_count=Count(
                "id", 
                filter=Q(first_check_in_at__isnull=False, last_check_out_at__isnull=True)
            ),
            # Checked out checks: has recorded both a check-in and check-out event
            checked_out_count=Count(
                "id", 
                filter=Q(first_check_in_at__isnull=False, last_check_out_at__isnull=False)
            ),
            # Missing checkout exception checks
            missing_checkout_count=Count(
                "id", 
                filter=Q(first_check_in_at__isnull=False, last_check_out_at__isnull=True, is_auto_closed=False, needs_review=True)
            )
        )

        present = aggregations["present_count"] or 0
        leaves = aggregations["leave_count"] or 0
        not_checked_in = max(0, total_active_employees - (present + leaves))
        
        attendance_pct = (present / total_active_employees * 100.0) if total_active_employees > 0 else 0.0

        return {
            "total_employees": total_active_employees,
            "present": present,
            "currently_working": aggregations["currently_working_count"] or 0,
            "checked_out": aggregations["checked_out_count"] or 0,
            "not_checked_in": not_checked_in,
            "on_leave": leaves,
            "absent": aggregations["absent_count"] or 0,
            "late": aggregations["late_count"] or 0,
            "early_exit": aggregations["early_exit_count"] or 0,
            "missing_checkout": aggregations["missing_checkout_count"] or 0,
            "needs_review": aggregations["review_required_count"] or 0,
            "company_attendance_percentage": round(attendance_pct, 2)
        }

    @classmethod
    def get_department_summaries(cls, *, company: Company, target_date: datetime.date) -> list:
        """
        Compiles performance metrics grouped by corporate departments using foreign key IDs.
        """
        # Aggregate stats directly inside the database grouped by department references
        dept_data = DailyAttendance.objects.filter(
            company=company, 
            attendance_date=target_date,
            membership__department__isnull=False
        ).values(
            "membership__department_id",
            "membership__department__name"
        ).annotate(
            total_employees=Count("membership_id", distinct=True),
            present=Count("id", filter=Q(is_present=True)),
            currently_working=Count("id", filter=Q(first_check_in_at__isnull=False, last_check_out_at__isnull=True)),
            on_leave=Count("id", filter=Q(is_leave=True)),
            absent=Count("id", filter=Q(is_absent=True)),
            late=Count("id", filter=Q(is_late=True)),
            review_count=Count("id", filter=Q(needs_review=True))
        ).order_by("membership__department__name")

        summaries = []
        for item in dept_data:
            emp_count = item["total_employees"] or 0
            present_count = item["present"] or 0
            pct = (present_count / emp_count * 100.0) if emp_count > 0 else 0.0
            
            summaries.append({
                "department_id": item["membership__department_id"],
                "department_name": item["membership__department__name"],
                "employee_count": emp_count,
                "present": present_count,
                "currently_working": item["currently_working"] or 0,
                "leave": item["on_leave"] or 0,
                "absent": item["absent"] or 0,
                "late": item["late"] or 0,
                "attendance_percentage": round(pct, 2),
                "review_count": item["review_count"] or 0
            })
        return summaries

    @classmethod
    def get_shift_summaries(cls, *, company: Company, target_date: datetime.date) -> list:
        """
        Aggregations mapping employee counts and lates across frozen schedule snapshots.
        """
        # Parse JSON snapshot variables at the database level using Django data field query paths
        shift_data = DailyAttendance.objects.filter(
            company=company,
            attendance_date=target_date,
            schedule_snapshot__has_key="shift_id"
        ).values(
            "schedule_snapshot__shift_id",
            "schedule_snapshot__shift_name"
        ).annotate(
            assigned=Count("id"),
            checked_in=Count("id", filter=Q(first_check_in_at__isnull=False)),
            working=Count("id", filter=Q(first_check_in_at__isnull=False, last_check_out_at__isnull=True)),
            completed=Count("id", filter=Q(first_check_in_at__isnull=False, last_check_out_at__isnull=False)),
            late=Count("id", filter=Q(is_late=True))
        ).order_by("schedule_snapshot__shift_name")

        summaries = []
        for item in shift_data:
            assigned = item["assigned"] or 0
            checked_in = item["checked_in"] or 0
            
            summaries.append({
                "shift_id": item["schedule_snapshot__shift_id"],
                "shift_name": item["schedule_snapshot__shift_name"] or "Standard Corporate Shift",
                "assigned_employees": assigned,
                "checked_in": checked_in,
                "working": item["working"] or 0,
                "completed": item["completed"] or 0,
                "not_checked_in": max(0, assigned - checked_in),
                "late": item["late"] or 0
            })
        return summaries