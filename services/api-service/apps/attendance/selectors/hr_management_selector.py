# apps/attendance/selectors/hr_management_selector.py
import datetime
from typing import Optional
from django.db.models import QuerySet, Count, Q
from apps.companies.models import Company
from apps.attendance.models.daily_attendance import DailyAttendance, DailyAttendanceStatus

class HRAttendanceManagementSelector:
    """
    Selector executing multi-tenant isolated queries.
    Implements optimized query pre-fetching to eliminate N+1 overhead.
    """

    @classmethod
    def get_base_hr_queryset(cls, *, company: Company) -> QuerySet[DailyAttendance]:
        return DailyAttendance.objects.filter(company=company).select_related(
            "membership",
            "membership__user",
            "membership__department",
            "finalized_by",
            "finalized_by__user"
        )

    @classmethod
    def list_daily_attendance_ledger(
        cls,
        *,
        company: Company,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
        status: Optional[str] = None,
        membership_id: Optional[int] = None,
        department_id: Optional[int] = None,
        review_required: Optional[bool] = None,
        is_finalized: Optional[bool] = None,
        search_query: Optional[str] = None,
        ordering: str = "-attendance_date"
    ) -> QuerySet[DailyAttendance]:
        queryset = cls.get_base_hr_queryset(company=company)

        if date_from:
            queryset = queryset.filter(attendance_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(attendance_date__lte=date_to)
        if status:
            queryset = queryset.filter(attendance_status=status)
        if membership_id:
            queryset = queryset.filter(membership_id=membership_id)
        if department_id:
            queryset = queryset.filter(membership__department_id=department_id)
        if review_required is not None:
            queryset = queryset.filter(needs_review=review_required)
        if is_finalized is not None:
            queryset = queryset.filter(finalized_at__isnull=not is_finalized)

        if search_query:
            queryset = queryset.filter(
                Q(membership__user__first_name__icontains=search_query) |
                Q(membership__user__last_name__icontains=search_query) |
                Q(membership__user__username__icontains=search_query)
            )

        # FIXED: Changed from 'membership__attendanceevent_set' to match the related_name definition
        return queryset.prefetch_related("membership__attendance_events").order_by(ordering)

    @classmethod
    def get_aggregated_dashboard_summary(cls, *, company: Company, target_date: datetime.date) -> dict:
        aggregations = DailyAttendance.objects.filter(
            company=company, attendance_date=target_date
        ).aggregate(
            present=Count("id", filter=Q(attendance_status=DailyAttendanceStatus.PRESENT)),
            absent=Count("id", filter=Q(attendance_status=DailyAttendanceStatus.ABSENT)),
            half_day=Count("id", filter=Q(attendance_status=DailyAttendanceStatus.HALF_DAY)),
            late=Count("id", filter=Q(is_late=True)),
            leave=Count("id", filter=Q(attendance_status=DailyAttendanceStatus.LEAVE)),
            holiday=Count("id", filter=Q(attendance_status=DailyAttendanceStatus.HOLIDAY)),
            weekend=Count("id", filter=Q(attendance_status=DailyAttendanceStatus.WEEKEND)),
            review=Count("id", filter=Q(needs_review=True))
        )

        dept_raw = DailyAttendance.objects.filter(
            company=company, attendance_date=target_date
        ).values(
            "membership__department_id",
            "membership__department__name"
        ).annotate(
            present=Count("id", filter=Q(attendance_status=DailyAttendanceStatus.PRESENT)),
            absent=Count("id", filter=Q(attendance_status=DailyAttendanceStatus.ABSENT)),
            late=Count("id", filter=Q(is_late=True))
        )

        department_breakdown = [
            {
                "department_id": item["membership__department_id"],
                "department_name": item["membership__department__name"] or "Unassigned Department",
                "present_count": item["present"],
                "absent_count": item["absent"],
                "late_count": item["late"]
            }
            for item in dept_raw
        ]

        return {
            "statistics": {
                "present": aggregations["present"] or 0,
                "absent": aggregations["absent"] or 0,
                "half_day": aggregations["half_day"] or 0,
                "late": aggregations["late"] or 0,
                "leave": aggregations["leave"] or 0,
                "holiday": aggregations["holiday"] or 0,
                "weekend": aggregations["weekend"] or 0,
                "review_required": aggregations["review"] or 0,
            },
            "department_breakdown": department_breakdown
        }