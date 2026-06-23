from rest_framework import status
from django.utils import timezone
from apps.core.api_response import ApiResponse
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.standers_pagination import StandardLimitOffsetPagination
from apps.attendance.services.attendance_history_service import AttendanceHistoryService
from apps.attendance.selectors.daily_attendance_selector import DailyAttendanceSelector
from apps.attendance.api.v1.serializers.daily_attendance_serializers import (
    DailyAttendanceListSerializer,
    AttendanceStatisticsSerializer,
    AttendanceDetailResponseSerializer,
)


class AttendanceManagementListAPI(BaseCompanyAPIView):
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


class AttendanceManagementDetailAPI(BaseCompanyAPIView):
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


class AttendanceManagementAnalyticsAPI(BaseCompanyAPIView):
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
