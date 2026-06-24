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

    Response Shape (ApiResponse wrapper + pagination):
    {
        "success": true,
        "message": "Success",
        "data": {
            "count": 30,
            "next": null,
            "previous": null,
            "results": [
                {
                    "id": 1,
                    "attendance_date": "2026-06-23",
                    "attendance_status": "PRESENT",
                    ...
                }
            ]
        }
    }
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

        # FIX: paginator.get_paginated_response() returns a Response object.
        # We extract its .data (dict with count/next/previous/results) 
        # and wrap it in ApiResponse.
        paginated_response = paginator.get_paginated_response(serializer.data)
        return ApiResponse.success(data=paginated_response.data)


class MyAttendanceSummaryAPI(BaseCompanyAPIView):
    """
    GET /attendance/v1/my-attendance/summary/
    Returns attendance summary cards for the employee.

    Response Shape:
    {
        "success": true,
        "message": "Success",
        "data": {
            "total_days": 23,
            "present_days": 14,
            "absent_days": 3,
            "late_days": 5,
            "attendance_percentage": 60.87,
            "total_work_hours": 90.65,
            "total_overtime_hours": 0.0,
            "present_sparkline": [1, 1, 0, 1, 1, 1, 1],
            ...
        }
    }
    """
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request, *args, **kwargs):
        summary = AttendanceHistoryService.build_employee_summary_cards(
            membership=request.membership
        )

        serializer = AttendanceSummarySerializer(summary)
        return ApiResponse.success(data=serializer.data)


class MyAttendanceTrendsView(BaseCompanyAPIView):
    """
    GET /attendance/v1/my-attendance/trends/
    Returns weekly and monthly attendance trends.

    Response Shape:
    {
        "success": true,
        "message": "Success",
        "data": {
            "monthly": [
                {"month": 5, "present": 4, "absent": 1, "late": 1, "leave": 0, "total": 7},
                {"month": 6, "present": 14, "absent": 3, "late": 5, "leave": 0, "total": 23}
            ],
            "weekly": [
                {"week_start": "2026-05-25", "week_end": "2026-05-31", "present_days": 4, "total_days": 5, "percentage": 80.0}
            ]
        }
    }
    """
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request, *args, **kwargs):
        year = int(request.query_params.get("year", timezone.now().year))
        trends = AttendanceHistoryService.build_trend_graphs(
            membership=request.membership,
            year=year,
        )

        # trends = { "monthly": [ {...}, {...} ], "weekly": [ {...}, {...} ] }
        # 
        # FIX: AttendanceTrendSerializer is a SINGLE object serializer.
        # It expects { month, present, absent, late, leave, total }.
        # We have a LIST of such objects in trends["monthly"].
        # Use many=True to serialize the list.
        monthly_serializer = AttendanceTrendSerializer(trends["monthly"], many=True)

        # Weekly data is already dicts from the service, but we should serialize
        # for consistency. Create a simple serializer or pass as-is.
        # For now, pass weekly as-is since it's already in the correct format.
        # If you want strict validation, add AttendanceWeeklyTrendSerializer.

        data = {
            "monthly": monthly_serializer.data,
            "weekly": trends["weekly"],
        }

        return ApiResponse.success(data=data)


class MyAttendanceCalendarAPI(BaseCompanyAPIView):
    """
    GET /attendance/v1/my-attendance/calendar/
    Returns calendar data for a specific month.

    Response Shape:
    {
        "success": true,
        "message": "Success",
        "data": [
            {"date": "2026-06-01", "status": "PRESENT", "is_late": true, ...},
            {"date": "2026-06-02", "status": "PRESENT", "is_late": false, ...}
        ]
    }
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

        # FIX: calendar_data is a LIST of dicts.
        # AttendanceCalendarSerializer is a SINGLE object serializer.
        # Use many=True to serialize the entire list.
        serializer = AttendanceCalendarSerializer(calendar_data, many=True)

        return ApiResponse.success(data=serializer.data)


class MyAttendanceDetailAPI(BaseCompanyAPIView):
    """
    GET /attendance/v1/my-attendance/<id>/
    Returns daily attendance detail with event timeline.
    """
    required_permissions = {"GET": "tenant.attendance.view"}

    # ✅ FIXED: Name changed from 'record_id' to 'pk' to match the urls.py path pattern capture variable name
    def get(self, request, pk, *args, **kwargs):
        # Security: ensure employee can only access their own records
        payload = AttendanceHistoryService.build_detail_screen_payload(
            record_id=pk, # Passes the ID safely to your existing service layer logic
            company=request.company,
            membership=request.membership,
        )
        if not payload:
            return ApiResponse.error(message="Record not found.", status=status.HTTP_404_NOT_FOUND)

        serializer = AttendanceDetailResponseSerializer(payload)
        return ApiResponse.success(data=serializer.data)