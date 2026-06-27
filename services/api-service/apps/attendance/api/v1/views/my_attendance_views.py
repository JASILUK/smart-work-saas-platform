from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from apps.core.api_response import ApiResponse
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.standers_pagination import PaginationAdapter, StandardLimitOffsetPagination
from apps.attendance.services.attendance_history_service import AttendanceHistoryService
from apps.attendance.selectors.daily_attendance_selector import DailyAttendanceSelector
from apps.attendance.api.v1.serializers.daily_attendance_serializers import (
    DailyAttendanceListSerializer,
    AttendanceSummarySerializer,
    AttendanceCalendarSerializer,
    AttendanceDetailResponseSerializer,
    MonthlyTrendSerializer,
    WeeklyTrendSerializer,
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

        # ── FIX: Priority = explicit date_from/date_to > month/year fallback ──
        if date_from or date_to:
            # User applied custom date range — use it directly
            from_date = (
                timezone.datetime.strptime(date_from, "%Y-%m-%d").date()
                if date_from
                else None
            )
            to_date = (
                timezone.datetime.strptime(date_to, "%Y-%m-%d").date()
                if date_to
                else None
            )
        elif year and month:
            # No custom dates — fall back to full month range
            year = int(year)
            month = int(month)
            from_date = timezone.datetime(year, month, 1).date()
            if month == 12:
                to_date = timezone.datetime(year + 1, 1, 1).date() - timezone.timedelta(days=1)
            else:
                to_date = timezone.datetime(year, month + 1, 1).date() - timezone.timedelta(days=1)
        else:
            from_date = None
            to_date = None

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

        paginated_response = paginator.get_paginated_response(serializer.data)
        return ApiResponse.success(data=paginated_response.data)

class MyAttendanceSummaryAPI(BaseCompanyAPIView):
    """
    GET /attendance/v1/my-attendance/summary/
    
    Query params:
        ?date_from=2026-06-01&date_to=2026-06-15
        ?month=6&year=2026          (legacy, still supported)
    
    Response:
    {
        "success": true,
        "message": "Success",
        "data": { ... }
    }
    """
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request, *args, **kwargs):
        membership = request.membership
        
        # ── Parse query params ──
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        month = request.query_params.get("month")
        year = request.query_params.get("year")
        
        today = timezone.localtime(timezone.now()).date()
        
        # ── Build date range ──
        if year and month:
            # Month view: extract bounds safely
            year = int(year)
            month = int(month)
            from_date = timezone.datetime(year, month, 1).date()
            
            # Determine last true calendar day of the month
            if month == 12:
                last_day_of_month = timezone.datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                last_day_of_month = timezone.datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            # FIXED: Do not summarize the future for the current year/month configuration
            if year == today.year and month == today.month:
                to_date = today
            else:
                to_date = last_day_of_month
                
        elif date_from or date_to:
            # Custom date range
            from_date = timezone.datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else today.replace(day=1)
            to_date = timezone.datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else today
        else:
            # Default: current month to today
            from_date = today.replace(day=1)
            to_date = today
        
        # ── Delegate to service ──
        data = AttendanceHistoryService.build_filtered_summary(
            membership=membership,
            date_from=from_date,
            date_to=to_date,
        )
        
        serializer = AttendanceSummarySerializer(data)
        return ApiResponse.success(data=serializer.data)

# ─── View ──────────────────────────────────────────────────────────────────────
class MyAttendanceTrendsView(BaseCompanyAPIView):
    """
    GET /attendance/v1/my-attendance/trends/?year=2026&limit=12&offset=0
    
    Query params:
      - year: filter year (default: current year)
      - limit: items per page for WEEKLY only (default: 20)
      - offset: skip N items for WEEKLY only (default: 0)
    
    Response:
    {
        "success": true,
        "message": "Success",
        "data": {
            "year": 2026,
            "monthly": [ ... ],
            "weekly": [ ... ],
            "count": 52,
            "next": "?limit=12&offset=12",
            "previous": null
        }
    }
    """
    required_permissions = {"GET": "tenant.attendance.view"}
    pagination_class = StandardLimitOffsetPagination  # ← your EXISTING class, UNCHANGED

    def get(self, request, *args, **kwargs):
        year = int(request.query_params.get("year", timezone.now().year))
        
        trends = AttendanceHistoryService.build_trend_graphs(
            membership=request.membership, year=year
        )
        
        # Monthly: always return ALL (max 12, tiny data)
        monthly_serialized = MonthlyTrendSerializer(trends["monthly"], many=True).data
        
        # Weekly: paginate with your EXISTING class
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(trends["weekly"], request, view=self)
        weekly_serialized = WeeklyTrendSerializer(page, many=True).data
        
        # Extract metadata using ADAPTER (works with any pagination class)
        meta = PaginationAdapter.get_metadata(paginator, page)
        
        return ApiResponse.success(data={
            "year": year,
            "monthly": monthly_serialized,
            "weekly": weekly_serialized,
            "count": meta["count"],
            "next": meta["next"],
            "previous": meta["previous"],
        })


class MyAttendanceCalendarAPI(BaseCompanyAPIView):
    """
    GET /attendance/v1/my-attendance/calendar/?year=2026&month=6
    
    Returns ALL days of the month (1-31) with merged status:
    - HOLIDAY (from company holiday calendar)
    - WEEKEND (from company work schedule)
    - PRESENT/ABSENT/LATE/etc. (from attendance records)
    - NOT_MARKED (no record)
    
    Response:
    {
        "success": true,
        "message": "Success",
        "data": [
            {
                "date": "2026-06-01",
                "day_of_month": 1,
                "day_of_week": 0,
                "is_weekend": false,
                "is_holiday": false,
                "holiday_name": null,
                "status": "PRESENT",
                "is_late": true,
                "is_half_day": false,
                "is_leave": false,
                "check_in": "09:15",
                "check_out": "18:00",
                "work_hours": 8.25
            },
            {
                "date": "2026-06-05",
                "day_of_month": 5,
                "day_of_week": 4,
                "is_weekend": false,
                "is_holiday": true,
                "holiday_name": "Company Foundation Day",
                "status": "HOLIDAY",
                "is_late": false,
                "is_half_day": false,
                "is_leave": false,
                "check_in": null,
                "check_out": null,
                "work_hours": null
            },
            {
                "date": "2026-06-07",
                "day_of_month": 7,
                "day_of_week": 6,
                "is_weekend": true,
                "is_holiday": false,
                "holiday_name": null,
                "status": "WEEKEND",
                ...
            }
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