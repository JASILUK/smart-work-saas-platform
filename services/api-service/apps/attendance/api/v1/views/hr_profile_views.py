# apps/attendance/api/v1/views/hr_profile_views.py
"""
HR Employee Attendance Profile API View

Provides fine-grained timesheet histories, period KPIs, and rolling analytics
for an individual employee profile view. This is the central HR attendance workspace
endpoint consumed by the frontend Employee Attendance Profile page.

Endpoint: GET /attendance/v1/hr-management/employees/<membership_id>/
"""

from rest_framework import status
from django.utils import timezone

from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse
from apps.core.standers_pagination import (
    StandardLimitOffsetPagination,
    PaginationAdapter
)

from apps.attendance.services.hr_profile_service import HREmployeeProfileService
from apps.attendance.api.v1.serializers.hr_profile_serializers import (
    HREmployeeProfileHeaderSerializer,
    HRProfileSummarySerializer,
    HRProfileTrendChartsSerializer,
    HRProfileStatusDistributionSerializer,
    HRProfileAttendanceRecordRowSerializer
)


class HREmployeeAttendanceProfileAPIView(BaseCompanyAPIView):
    """
    Production-grade employee attendance profile analytics endpoint.

    Returns a comprehensive dataset containing:
    - Employee header metadata
    - Period summary KPIs (working days, attendance %, averages, totals)
    - Multi-granularity trend charts (daily, weekly, monthly)
    - Status distribution breakdown
    - Late, work hours, and overtime trend lines
    - Paginated, filterable attendance records

    Query Parameters:
        date_from (str): ISO 8601 date (YYYY-MM-DD). Defaults to first day of current month.
        date_to (str): ISO 8601 date (YYYY-MM-DD). Defaults to today.
        attendance_status (str): Filter by DailyAttendanceStatus value.
        late_only (bool): Filter records with late_minutes > 0.
        needs_review (bool): Filter records flagged for HR review.
        auto_closed (bool): Filter auto-closed records.
        missing_checkout (bool): Filter records with missing checkouts.
        holiday_only (bool): Filter holiday records.
        weekend_only (bool): Filter weekend records.
        leave_only (bool): Filter approved leave records.
        ordering (str): Sort column. Allowed values defined in AttendanceRecordSelector.
    """

    required_permissions = {
        "GET": "tenant.attendance.view",
    }

    def get(self, request, membership_id, *args, **kwargs):
        """
        Compile and return the complete employee attendance profile dataset.
        """
        # 1. Delegate all business logic to the service layer
        profile_dataset = HREmployeeProfileService.compile_profile_dataset(
            company=request.company,
            membership_id=int(membership_id),
            query_params=request.query_params.dict()
        )

        # 2. Serialize structural modules using dedicated serializers
        employee_serialized = HREmployeeProfileHeaderSerializer(
            profile_dataset["employee"]
        ).data

        summary_serialized = HRProfileSummarySerializer(
            profile_dataset["summary"]
        ).data

        charts_serialized = HRProfileTrendChartsSerializer(
            profile_dataset["charts"]
        ).data

        status_distribution_serialized = HRProfileStatusDistributionSerializer(
            profile_dataset["status_distribution"], many=True
        ).data

        # 3. Apply standard limit-offset pagination for records
        paginator = StandardLimitOffsetPagination()
        paginated_records = paginator.paginate_queryset(
            profile_dataset["records_queryset"], request, view=self
        )

        records_serialized = HRProfileAttendanceRecordRowSerializer(
            paginated_records, many=True
        ).data
        pagination_meta = PaginationAdapter.get_metadata(paginator, paginated_records)

        # 4. Assemble the complete response envelope
        response_data = {
            "employee": employee_serialized,
            "summary": summary_serialized,
            "charts": {
                "daily": charts_serialized.get("daily", []),
                "weekly": charts_serialized.get("weekly", []),
                "monthly": charts_serialized.get("monthly", []),
                "status_distribution": status_distribution_serialized,
                "late_trend": charts_serialized.get("late_trend", []),
                "work_hours_trend": charts_serialized.get("work_hours_trend", []),
                "overtime_trend": charts_serialized.get("overtime_trend", []),
            },
            "records": {
                "results": records_serialized,
                "pagination": pagination_meta
            },
            "metadata": profile_dataset["metadata"]
        }

        return ApiResponse.success(
            data=response_data,
            message="Employee attendance profile analytics compiled successfully.",
            status=status.HTTP_200_OK
        )