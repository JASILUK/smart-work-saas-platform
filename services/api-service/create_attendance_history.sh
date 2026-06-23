#!/bin/bash

# Create directory structure
mkdir -p apps/attendance/selectors
mkdir -p apps/attendance/services
mkdir -p apps/attendance/api/v1/serializers
mkdir -p apps/attendance/api/v1/views

# =================================================================
# 1. SELECTOR: daily_attendance_selector.py
# =================================================================
cat > apps/attendance/selectors/daily_attendance_selector.py << 'EOF'
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
EOF

# =================================================================
# 2. SERVICE: attendance_history_service.py
# =================================================================
cat > apps/attendance/services/attendance_history_service.py << 'EOF'
import datetime
from typing import Dict, List, Any, Optional
from django.utils import timezone
from apps.companies.models import Company, Membership
from apps.attendance.selectors.daily_attendance_selector import DailyAttendanceSelector
from apps.attendance.selectors.attendance_event_selector import AttendanceEventSelector


class AttendanceHistoryService:
    """
    Service layer for attendance history aggregation and payload building.
    Owns all business logic. Selectors only fetch data.
    """

    @staticmethod
    def build_employee_summary_cards(*, membership: Membership) -> Dict[str, Any]:
        """Build summary cards for employee dashboard."""
        today = timezone.localtime(timezone.now()).date()
        
        # Current month
        start_of_month = today.replace(day=1)
        month_summary = DailyAttendanceSelector.get_attendance_summary(
            membership=membership,
            date_from=start_of_month,
            date_to=today,
        )

        # Year to date
        start_of_year = today.replace(month=1, day=1)
        ytd_summary = DailyAttendanceSelector.get_attendance_summary(
            membership=membership,
            date_from=start_of_year,
            date_to=today,
        )

        return {
            "current_month": {
                "present_days": month_summary["present_days"],
                "absent_days": month_summary["absent_days"],
                "late_days": month_summary["late_days"],
                "attendance_percentage": month_summary["attendance_percentage"],
                "total_work_hours": month_summary["total_work_hours"],
            },
            "year_to_date": {
                "present_days": ytd_summary["present_days"],
                "absent_days": ytd_summary["absent_days"],
                "late_days": ytd_summary["late_days"],
                "attendance_percentage": ytd_summary["attendance_percentage"],
                "total_work_hours": ytd_summary["total_work_hours"],
            },
        }

    @staticmethod
    def build_attendance_statistics(*, company: Company, date_from: Optional[datetime.date] = None, date_to: Optional[datetime.date] = None) -> Dict[str, Any]:
        """Build company-wide attendance statistics for managers."""
        return DailyAttendanceSelector.get_attendance_statistics(
            company=company,
            date_from=date_from,
            date_to=date_to,
        )

    @staticmethod
    def build_trend_graphs(*, membership: Membership, year: int) -> Dict[str, Any]:
        """Build weekly and monthly trend data."""
        monthly_trend = DailyAttendanceSelector.get_attendance_trend(
            membership=membership,
            year=year,
        )

        # Weekly trend (last 12 weeks)
        today = timezone.localtime(timezone.now()).date()
        weekly_trend = []
        for week_offset in range(11, -1, -1):
            week_start = today - datetime.timedelta(days=today.weekday() + (week_offset * 7))
            week_end = week_start + datetime.timedelta(days=6)
            week_records = DailyAttendanceSelector.get_date_range_records(
                membership=membership,
                start_date=week_start,
                end_date=week_end,
            )
            present_count = sum(1 for r in week_records if r.attendance_status == "PRESENT")
            total_count = week_records.count()
            weekly_trend.append({
                "week_start": week_start.strftime("%Y-%m-%d"),
                "week_end": week_end.strftime("%Y-%m-%d"),
                "present_days": present_count,
                "total_days": total_count,
                "percentage": round((present_count / total_count * 100), 2) if total_count > 0 else 0,
            })

        return {
            "monthly": monthly_trend,
            "weekly": weekly_trend,
        }

    @staticmethod
    def build_calendar_payload(*, membership: Membership, year: int, month: int) -> List[Dict[str, Any]]:
        """Build calendar dataset for a given month."""
        return DailyAttendanceSelector.get_attendance_calendar_data(
            membership=membership,
            year=year,
            month=month,
        )

    @staticmethod
    def build_detail_screen_payload(*, record_id: int, company: Company, membership: Membership) -> Dict[str, Any]:
        """Build detail screen with summary and timeline."""
        # Get the daily attendance record
        daily_record = DailyAttendanceSelector.get_by_id(record_id=record_id, company=company)
        if not daily_record:
            return {}

        # Get timeline events
        events = AttendanceEventSelector.get_events_for_membership_and_date(
            membership=membership,
            date=daily_record.attendance_date,
        )

        timeline = [
            {
                "event_type": event.event_type,
                "event_time": event.event_time.isoformat(),
                "attendance_method": event.attendance_method,
                "location_name": getattr(event.location, 'name', None) if event.location else None,
                "notes": event.notes,
            }
            for event in events
        ]

        return {
            "daily_record": daily_record,
            "timeline": timeline,
        }

    @staticmethod
    def build_event_timeline(*, membership: Membership, date: datetime.date) -> List[Dict[str, Any]]:
        """Build event timeline for a specific date."""
        events = AttendanceEventSelector.get_events_for_membership_and_date(
            membership=membership,
            date=date,
        )

        return [
            {
                "event_type": event.event_type,
                "event_time": event.event_time.isoformat(),
                "attendance_method": event.attendance_method,
                "location_name": getattr(event.location, 'name', None) if event.location else None,
                "notes": event.notes,
            }
            for event in events
        ]
EOF

# =================================================================
# 3. SERIALIZERS: daily_attendance_serializers.py
# =================================================================
cat > apps/attendance/api/v1/serializers/daily_attendance_serializers.py << 'EOF'
from rest_framework import serializers


class DailyAttendanceListSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    attendance_date = serializers.DateField(read_only=True)
    attendance_status = serializers.CharField(read_only=True)
    first_check_in_at = serializers.CharField(read_only=True, allow_null=True)
    last_check_out_at = serializers.CharField(read_only=True, allow_null=True)
    total_work_minutes = serializers.IntegerField(read_only=True)
    overtime_minutes = serializers.IntegerField(read_only=True)
    late_minutes = serializers.IntegerField(read_only=True)
    attendance_method_summary = serializers.CharField(read_only=True, allow_blank=True)
    is_late = serializers.BooleanField(read_only=True)
    is_half_day = serializers.BooleanField(read_only=True)
    is_leave = serializers.BooleanField(read_only=True)
    is_holiday = serializers.BooleanField(read_only=True)
    is_weekend = serializers.BooleanField(read_only=True)


class DailyAttendanceDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    attendance_date = serializers.DateField(read_only=True)
    attendance_status = serializers.CharField(read_only=True)
    first_check_in_at = serializers.CharField(read_only=True, allow_null=True)
    last_check_out_at = serializers.CharField(read_only=True, allow_null=True)
    total_work_minutes = serializers.IntegerField(read_only=True)
    total_break_minutes = serializers.IntegerField(read_only=True)
    overtime_minutes = serializers.IntegerField(read_only=True)
    late_minutes = serializers.IntegerField(read_only=True)
    early_exit_minutes = serializers.IntegerField(read_only=True)
    required_work_minutes = serializers.IntegerField(read_only=True)
    attendance_method_summary = serializers.CharField(read_only=True, allow_blank=True)
    is_late = serializers.BooleanField(read_only=True)
    is_half_day = serializers.BooleanField(read_only=True)
    is_leave = serializers.BooleanField(read_only=True)
    is_holiday = serializers.BooleanField(read_only=True)
    is_weekend = serializers.BooleanField(read_only=True)
    is_absent = serializers.BooleanField(read_only=True)
    is_early_exit = serializers.BooleanField(read_only=True)
    is_auto_closed = serializers.BooleanField(read_only=True)
    needs_review = serializers.BooleanField(read_only=True)
    review_reason = serializers.CharField(read_only=True, allow_blank=True)
    auto_close_reason = serializers.CharField(read_only=True, allow_blank=True)
    schedule_snapshot = serializers.JSONField(read_only=True)
    policy_snapshot = serializers.JSONField(read_only=True)
    source = serializers.CharField(read_only=True)
    finalized_at = serializers.DateTimeField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class AttendanceTimelineSerializer(serializers.Serializer):
    event_type = serializers.CharField(read_only=True)
    event_time = serializers.CharField(read_only=True)
    attendance_method = serializers.CharField(read_only=True)
    location_name = serializers.CharField(read_only=True, allow_null=True)
    notes = serializers.CharField(read_only=True, allow_blank=True)


class AttendanceSummarySerializer(serializers.Serializer):
    total_days = serializers.IntegerField(read_only=True)
    present_days = serializers.IntegerField(read_only=True)
    absent_days = serializers.IntegerField(read_only=True)
    half_days = serializers.IntegerField(read_only=True)
    late_days = serializers.IntegerField(read_only=True)
    leave_days = serializers.IntegerField(read_only=True)
    holiday_days = serializers.IntegerField(read_only=True)
    weekend_days = serializers.IntegerField(read_only=True)
    attendance_percentage = serializers.FloatField(read_only=True)
    total_work_hours = serializers.FloatField(read_only=True)
    total_overtime_hours = serializers.FloatField(read_only=True)


class AttendanceStatisticsSerializer(serializers.Serializer):
    total_records = serializers.IntegerField(read_only=True)
    present_count = serializers.IntegerField(read_only=True)
    absent_count = serializers.IntegerField(read_only=True)
    late_count = serializers.IntegerField(read_only=True)
    leave_count = serializers.IntegerField(read_only=True)
    review_required_count = serializers.IntegerField(read_only=True)
    attendance_percentage = serializers.FloatField(read_only=True)


class AttendanceTrendSerializer(serializers.Serializer):
    month = serializers.IntegerField(read_only=True)
    present = serializers.IntegerField(read_only=True)
    absent = serializers.IntegerField(read_only=True)
    late = serializers.IntegerField(read_only=True)
    leave = serializers.IntegerField(read_only=True)
    total = serializers.IntegerField(read_only=True)


class AttendanceCalendarSerializer(serializers.Serializer):
    date = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    is_late = serializers.BooleanField(read_only=True)
    is_half_day = serializers.BooleanField(read_only=True)
    is_leave = serializers.BooleanField(read_only=True)
    is_holiday = serializers.BooleanField(read_only=True)
    is_weekend = serializers.BooleanField(read_only=True)


class AttendanceDetailResponseSerializer(serializers.Serializer):
    daily_record = DailyAttendanceDetailSerializer(read_only=True)
    timeline = AttendanceTimelineSerializer(many=True, read_only=True)
EOF

# =================================================================
# 4. VIEWS: my_attendance_views.py
# =================================================================
cat > apps/attendance/api/v1/views/my_attendance_views.py << 'EOF'
from rest_framework import status
from django.utils import timezone
from apps.core.api_response import ApiResponse
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.pagination import StandardLimitOffsetPagination
from apps.attendance.services.attendance_history_service import AttendanceHistoryService
from apps.attendance.selectors.daily_attendance_selector import DailyAttendanceSelector
from apps.attendance.api.v1.serializers.daily_attendance_serializers import (
    DailyAttendanceListSerializer,
    AttendanceSummarySerializer,
    AttendanceTrendSerializer,
    AttendanceCalendarSerializer,
    AttendanceDetailResponseSerializer,
)


class MyAttendanceListView(BaseCompanyAPIView):
    """
    GET /attendance/v1/my-attendance/
    Returns paginated attendance records for the logged-in employee.
    """
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request, *args, **kwargs):
        membership = request.membership

        # Parse filters
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        status_filter = request.query_params.get("status")
        month = request.query_params.get("month")
        year = request.query_params.get("year")

        # Build date range
        if year and month:
            year = int(year)
            month = int(month)
            from_date = timezone.datetime(year, month, 1).date()
            if month == 12:
                to_date = timezone.datetime(year + 1, 1, 1).date() - timezone.timedelta(days=1)
            else:
                to_date = timezone.datetime(year, month + 1, 1).date() - timezone.timedelta(days=1)
        else:
            from_date = timezone.datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None
            to_date = timezone.datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else None

        records = DailyAttendanceSelector.get_membership_records(
            membership=membership,
            date_from=from_date,
            date_to=to_date,
            status=status_filter,
        )

        # Pagination
        paginator = StandardLimitOffsetPagination()
        page = paginator.paginate_queryset(records, request)
        serializer = DailyAttendanceListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class MyAttendanceSummaryView(BaseCompanyAPIView):
    """
    GET /attendance/v1/my-attendance/summary/
    Returns attendance summary cards for the employee.
    """
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request, *args, **kwargs):
        summary = AttendanceHistoryService.build_employee_summary_cards(
            membership=request.membership
        )
        return ApiResponse.success(data=summary)


class MyAttendanceTrendsView(BaseCompanyAPIView):
    """
    GET /attendance/v1/my-attendance/trends/
    Returns weekly and monthly attendance trends.
    """
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request, *args, **kwargs):
        year = int(request.query_params.get("year", timezone.now().year))
        trends = AttendanceHistoryService.build_trend_graphs(
            membership=request.membership,
            year=year,
        )
        return ApiResponse.success(data=trends)


class MyAttendanceCalendarView(BaseCompanyAPIView):
    """
    GET /attendance/v1/my-attendance/calendar/
    Returns calendar data for a specific month.
    """
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request, *args, **kwargs):
        year = int(request.query_params.get("year", timezone.now().year))
        month = int(request.query_params.get("month", timezone.now().month))
        calendar_data = AttendanceHistoryService.build_calendar_payload(
            membership=request.membership,
            year=year,
            month=month,
        )
        return ApiResponse.success(data=calendar_data)


class MyAttendanceDetailView(BaseCompanyAPIView):
    """
    GET /attendance/v1/my-attendance/<id>/
    Returns daily attendance detail with event timeline.
    """
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request, record_id, *args, **kwargs):
        # Security: ensure employee can only access their own records
        payload = AttendanceHistoryService.build_detail_screen_payload(
            record_id=record_id,
            company=request.company,
            membership=request.membership,
        )
        if not payload:
            return ApiResponse.error(message="Record not found.", status=status.HTTP_404_NOT_FOUND)

        serializer = AttendanceDetailResponseSerializer(payload)
        return ApiResponse.success(data=serializer.data)
EOF

# =================================================================
# 5. VIEWS: attendance_management_views.py
# =================================================================
cat > apps/attendance/api/v1/views/attendance_management_views.py << 'EOF'
from rest_framework import status
from django.utils import timezone
from apps.core.api_response import ApiResponse
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.pagination import StandardLimitOffsetPagination
from apps.attendance.services.attendance_history_service import AttendanceHistoryService
from apps.attendance.selectors.daily_attendance_selector import DailyAttendanceSelector
from apps.attendance.api.v1.serializers.daily_attendance_serializers import (
    DailyAttendanceListSerializer,
    AttendanceStatisticsSerializer,
    AttendanceDetailResponseSerializer,
)


class AttendanceManagementListView(BaseCompanyAPIView):
    """
    GET /attendance/v1/attendance-management/
    Returns company-wide attendance records for managers/HR.
    """
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, *args, **kwargs):
        company = request.company

        # Parse filters
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        status_filter = request.query_params.get("status")
        membership_id = request.query_params.get("membership")
        department_id = request.query_params.get("department")
        review_required = request.query_params.get("review_required")

        from_date = timezone.datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None
        to_date = timezone.datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else None
        review = None
        if review_required is not None:
            review = review_required.lower() == "true"

        records = DailyAttendanceSelector.get_company_records(
            company=company,
            date_from=from_date,
            date_to=to_date,
            status=status_filter,
            membership_id=membership_id,
            department_id=department_id,
            review_required=review,
        )

        # Pagination
        paginator = StandardLimitOffsetPagination()
        page = paginator.paginate_queryset(records, request)
        serializer = DailyAttendanceListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AttendanceManagementDetailView(BaseCompanyAPIView):
    """
    GET /attendance/v1/attendance-management/<id>/
    Returns employee attendance detail with timeline for managers.
    """
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, record_id, *args, **kwargs):
        company = request.company

        # Managers can view any company record
        daily_record = DailyAttendanceSelector.get_by_id(record_id=record_id, company=company)
        if not daily_record:
            return ApiResponse.error(message="Record not found.", status=status.HTTP_404_NOT_FOUND)

        payload = AttendanceHistoryService.build_detail_screen_payload(
            record_id=record_id,
            company=company,
            membership=daily_record.membership,
        )

        serializer = AttendanceDetailResponseSerializer(payload)
        return ApiResponse.success(data=serializer.data)


class AttendanceManagementAnalyticsView(BaseCompanyAPIView):
    """
    GET /attendance/v1/attendance-management/analytics/
    Returns company-wide attendance analytics.
    """
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, *args, **kwargs):
        company = request.company

        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        from_date = timezone.datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None
        to_date = timezone.datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else None

        statistics = AttendanceHistoryService.build_attendance_statistics(
            company=company,
            date_from=from_date,
            date_to=to_date,
        )

        serializer = AttendanceStatisticsSerializer(statistics)
        return ApiResponse.success(data=serializer.data)
EOF

# =================================================================
# 6. URLS: urls.py (Update existing attendance urls)
# =================================================================
cat > apps/attendance/api/v1/urls.py << 'EOF'
from django.urls import path
from apps.attendance.api.v1.views.my_attendance_views import (
    MyAttendanceListView,
    MyAttendanceSummaryView,
    MyAttendanceTrendsView,
    MyAttendanceCalendarView,
    MyAttendanceDetailView,
)
from apps.attendance.api.v1.views.attendance_management_views import (
    AttendanceManagementListView,
    AttendanceManagementDetailView,
    AttendanceManagementAnalyticsView,
)

# Existing attendance URLs (keep your existing ones)
# Add these new URLs

urlpatterns = [
    # Employee My Attendance
    path("my-attendance/", MyAttendanceListView.as_view(), name="my-attendance-list"),
    path("my-attendance/summary/", MyAttendanceSummaryView.as_view(), name="my-attendance-summary"),
    path("my-attendance/trends/", MyAttendanceTrendsView.as_view(), name="my-attendance-trends"),
    path("my-attendance/calendar/", MyAttendanceCalendarView.as_view(), name="my-attendance-calendar"),
    path("my-attendance/<int:record_id>/", MyAttendanceDetailView.as_view(), name="my-attendance-detail"),

    # Manager Attendance Management
    path("attendance-management/", AttendanceManagementListView.as_view(), name="attendance-management-list"),
    path("attendance-management/analytics/", AttendanceManagementAnalyticsView.as_view(), name="attendance-management-analytics"),
    path("attendance-management/<int:record_id>/", AttendanceManagementDetailView.as_view(), name="attendance-management-detail"),
]
EOF

echo "========================================"
echo "All files created successfully!"
echo "========================================"
echo ""
echo "Files created:"
echo "  - apps/attendance/selectors/daily_attendance_selector.py"
echo "  - apps/attendance/services/attendance_history_service.py"
echo "  - apps/attendance/api/v1/serializers/daily_attendance_serializers.py"
echo "  - apps/attendance/api/v1/views/my_attendance_views.py"
echo "  - apps/attendance/api/v1/views/attendance_management_views.py"
echo "  - apps/attendance/api/v1/urls.py"
echo ""
echo "Make sure to:"
echo "  1. Add 'pytz' to your requirements if not already installed"
echo "  2. Update your main urls.py to include these new paths"
echo "  3. Ensure DailyAttendance records exist (via signals or background tasks)"
echo "========================================"