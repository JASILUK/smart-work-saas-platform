import datetime
from typing import Optional, List, Dict, Any
from django.db.models import QuerySet, Count, Q, Avg, Sum
from django.utils import timezone
from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance


class DailyAttendanceSelector:
    """
    Optimized data access selectors for DailyAttendance records.
    All queries are company-scoped and multi-tenant safe.
    """

    @classmethod
    def get_queryset(cls) -> QuerySet[DailyAttendance]:
        return DailyAttendance.objects.select_related(
            "membership",
            "membership__user",
            "membership__department",
            "company",
        )

    @classmethod
    def get_by_id(cls, *, record_id: int, company: Company) -> Optional[DailyAttendance]:
        return cls.get_queryset().filter(id=record_id, company=company).first()

    @classmethod
    def get_record_for_membership_and_date(
        cls, *, membership: Membership, date: datetime.date
    ) -> Optional[DailyAttendance]:
        return cls.get_queryset().filter(
            membership=membership, attendance_date=date
        ).first()

    @classmethod
    def get_membership_records(
        cls,
        *,
        membership: Membership,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
        status: Optional[str] = None,
    ) -> QuerySet[DailyAttendance]:
        queryset = cls.get_queryset().filter(membership=membership)
        if date_from:
            queryset = queryset.filter(attendance_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(attendance_date__lte=date_to)
        if status:
            queryset = queryset.filter(attendance_status=status)
        return queryset.order_by("-attendance_date")

    @classmethod
    def get_company_records(
        cls,
        *,
        company: Company,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
        status: Optional[str] = None,
        membership_id: Optional[int] = None,
        department_id: Optional[int] = None,
        review_required: Optional[bool] = None,
    ) -> QuerySet[DailyAttendance]:
        queryset = cls.get_queryset().filter(company=company)
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
        return queryset.order_by("-attendance_date")

    @classmethod
    def get_date_range_records(
        cls,
        *,
        membership: Membership,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> QuerySet[DailyAttendance]:
        return cls.get_queryset().filter(
            membership=membership,
            attendance_date__range=[start_date, end_date],
        ).order_by("attendance_date")

    # ------------------------------------------------------------------
    # ALIAS: get_records_for_date_range
    # Accepts BOTH naming conventions to support all callers:
    #   - AttendanceHistoryService uses: date_from, date_to
    #   - EmployeeDashboardService uses: start_date, end_date
    # ------------------------------------------------------------------
    @classmethod
    def get_records_for_date_range(
        cls,
        *,
        membership: Membership,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
    ) -> QuerySet[DailyAttendance]:
        """
        Flexible date range query supporting both naming conventions.
        Priority: start_date/end_date > date_from/date_to
        """
        _start = start_date or date_from
        _end = end_date or date_to

        if not _start or not _end:
            raise ValueError(
                "get_records_for_date_range requires either (start_date, end_date) "
                "or (date_from, date_to)"
            )

        return cls.get_date_range_records(
            membership=membership,
            start_date=_start,
            end_date=_end,
        )

    @classmethod
    def get_status_records(
        cls,
        *,
        company: Company,
        status: str,
        date: Optional[datetime.date] = None,
    ) -> QuerySet[DailyAttendance]:
        queryset = cls.get_queryset().filter(company=company, attendance_status=status)
        if date:
            queryset = queryset.filter(attendance_date=date)
        return queryset

    @classmethod
    def get_month_records(
        cls,
        *,
        membership: Membership,
        year: int,
        month: int,
    ) -> QuerySet[DailyAttendance]:
        return cls.get_queryset().filter(
            membership=membership,
            attendance_date__year=year,
            attendance_date__month=month,
        ).order_by("attendance_date")

    @classmethod
    def get_attendance_summary(
        cls,
        *,
        membership: Membership,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
    ) -> Dict[str, Any]:
        queryset = cls.get_queryset().filter(membership=membership)
        if date_from:
            queryset = queryset.filter(attendance_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(attendance_date__lte=date_to)

        total_days = queryset.count()
        present_days = queryset.filter(attendance_status="PRESENT").count()
        absent_days = queryset.filter(attendance_status="ABSENT").count()
        half_days = queryset.filter(is_half_day=True).count()
        late_days = queryset.filter(is_late=True).count()
        leave_days = queryset.filter(is_leave=True).count()
        holiday_days = queryset.filter(is_holiday=True).count()
        weekend_days = queryset.filter(is_weekend=True).count()

        total_work_minutes = queryset.aggregate(total=Sum("total_work_minutes"))["total"] or 0
        total_overtime_minutes = queryset.aggregate(total=Sum("overtime_minutes"))["total"] or 0

        attendance_percentage = round((present_days / total_days * 100), 2) if total_days > 0 else 0.0

        return {
            "total_days": total_days,
            "present_days": present_days,
            "absent_days": absent_days,
            "half_days": half_days,
            "late_days": late_days,
            "leave_days": leave_days,
            "holiday_days": holiday_days,
            "weekend_days": weekend_days,
            "attendance_percentage": attendance_percentage,
            "total_work_hours": round(total_work_minutes / 60, 2),
            "total_overtime_hours": round(total_overtime_minutes / 60, 2),
        }

    @classmethod
    def get_attendance_trend(
        cls,
        *,
        membership: Membership,
        year: int,
    ) -> List[Dict[str, Any]]:
        records = cls.get_queryset().filter(
            membership=membership,
            attendance_date__year=year,
        ).order_by("attendance_date")

        monthly_data = {}
        for record in records:
            month_key = record.attendance_date.month
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    "month": month_key,
                    "present": 0,
                    "absent": 0,
                    "late": 0,
                    "leave": 0,
                    "total": 0,
                }
            monthly_data[month_key]["total"] += 1
            if record.attendance_status == "PRESENT":
                monthly_data[month_key]["present"] += 1
            elif record.attendance_status == "ABSENT":
                monthly_data[month_key]["absent"] += 1
            if record.is_late:
                monthly_data[month_key]["late"] += 1
            if record.is_leave:
                monthly_data[month_key]["leave"] += 1

        return list(monthly_data.values())

    @classmethod
    def get_attendance_statistics(
        cls,
        *,
        company: Company,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
    ) -> Dict[str, Any]:
        queryset = cls.get_queryset().filter(company=company)
        if date_from:
            queryset = queryset.filter(attendance_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(attendance_date__lte=date_to)

        total_records = queryset.count()
        present_count = queryset.filter(attendance_status="PRESENT").count()
        absent_count = queryset.filter(attendance_status="ABSENT").count()
        late_count = queryset.filter(is_late=True).count()
        leave_count = queryset.filter(is_leave=True).count()
        review_count = queryset.filter(needs_review=True).count()

        attendance_percentage = round((present_count / total_records * 100), 2) if total_records > 0 else 0.0

        return {
            "total_records": total_records,
            "present_count": present_count,
            "absent_count": absent_count,
            "late_count": late_count,
            "leave_count": leave_count,
            "review_required_count": review_count,
            "attendance_percentage": attendance_percentage,
        }

    @classmethod
    def get_attendance_calendar_data(
        cls,
        *,
        membership: Membership,
        year: int,
        month: int,
    ) -> List[Dict[str, Any]]:
        records = cls.get_queryset().filter(
            membership=membership,
            attendance_date__year=year,
            attendance_date__month=month,
        ).order_by("attendance_date")

        return [
            {
                "date": record.attendance_date.strftime("%Y-%m-%d"),
                "status": record.attendance_status or "NOT_MARKED",
                "is_late": record.is_late,
                "is_half_day": record.is_half_day,
                "is_leave": record.is_leave,
                "is_holiday": record.is_holiday,
                "is_weekend": record.is_weekend,
            }
            for record in records
        ]

    @classmethod
    def get_weekly_records(
        cls,
        *,
        membership: Membership,
        year: int,
    ) -> List[Dict[str, Any]]:
        """
        Returns weekly attendance aggregates for the given year.
        Each week contains: week_start, week_end, present_days, total_days, percentage.
        """
        records = cls.get_queryset().filter(
            membership=membership,
            attendance_date__year=year,
        ).order_by("attendance_date")

        weekly_data: Dict[int, Dict[str, Any]] = {}
        for record in records:
            date = record.attendance_date
            iso_year, iso_week, _ = date.isocalendar()
            if iso_year != year:
                continue

            if iso_week not in weekly_data:
                monday = date - datetime.timedelta(days=date.weekday())
                sunday = monday + datetime.timedelta(days=6)
                weekly_data[iso_week] = {
                    "week_start": monday,
                    "week_end": sunday,
                    "present_days": 0,
                    "total_days": 0,
                }

            weekly_data[iso_week]["total_days"] += 1
            if record.attendance_status == "PRESENT":
                weekly_data[iso_week]["present_days"] += 1

        result = []
        for week_num in sorted(weekly_data.keys()):
            week = weekly_data[week_num]
            total = week["total_days"]
            present = week["present_days"]
            percentage = round((present / total * 100), 2) if total > 0 else 0.0
            result.append({
                "week_start": week["week_start"].strftime("%Y-%m-%d"),
                "week_end": week["week_end"].strftime("%Y-%m-%d"),
                "present_days": present,
                "total_days": total,
                "percentage": percentage,
            })

        return result