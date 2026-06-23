from rest_framework import status
from django.utils import timezone
from apps.core.api_response import ApiResponse
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.standers_pagination import StandardLimitOffsetPagination
from apps.attendance.services.attendance_history_service import AttendanceHistoryService
from apps.attendance.selectors.daily_attendance_selector import DailyAttendanceSelector
from apps.attendance.api.v1.serializers.daily_attendance_serializers import (
    DailyAttendanceListSerializer,
    AttendanceSummarySerializer,
    AttendanceTrendSerializer,
    AttendanceCalendarSerializer,
    AttendanceDetailResponseSerializer,
)


class MyAttendanceRecordsAPI(BaseCompanyAPIView):
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


class MyAttendanceSummaryAPI(BaseCompanyAPIView):
    """
    GET /attendance/v1/my-attendance/summary/
    Returns attendance summary cards for the employee.
    """
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request, *args, **kwargs):
        summary = AttendanceHistoryService.build_employee_summary_cards(
            membership=request.membership
        )

        serializer =AttendanceSummarySerializer(summary)
        return ApiResponse.success(data=serializer.data)


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

        serializer = AttendanceTrendSerializer(trends)
        return ApiResponse.success(data=serializer.data)


class MyAttendanceCalendarAPI(BaseCompanyAPIView):
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
        serializer = AttendanceCalendarSerializer(calendar_data)
        return ApiResponse.success(data=serializer.data)


class MyAttendanceDetailAPI(BaseCompanyAPIView):
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
