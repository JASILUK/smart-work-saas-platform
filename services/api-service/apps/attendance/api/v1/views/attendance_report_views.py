# apps/attendance/api/v1/views/attendance_report_views.py
"""
Attendance Report Processing Controller Endpoints

Provides administrative interfaces allowing HR metrics analysts to fetch 
consolidated workspace reports alongside summary aggregation metadata envelopes.
"""

from rest_framework import status
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse
from apps.core.standers_pagination import (
    StandardLimitOffsetPagination,
    PaginationAdapter,
)
from apps.attendance.services.attendance_report_service import AttendanceReportService
from apps.attendance.api.v1.serializers.attendance_report_serializers import AttendanceReportRowSerializer


class AttendanceReportAPIView(BaseCompanyAPIView):
    """
    Enterprise Compliance Attendance Reports API Controller.
    """
    required_permissions = {
        "GET": "tenant.attendance.manage"
    }

    def get(self, request, *args, **kwargs):
        """
        Assembles, filters, and paginates workspace performance statistics.
        """
        # 1. Capture payload parameters directly
        query_params = request.query_params.dict()

        # 2. Delegate data composition rules cleanly down to the service layer
        queryset, summary, filter_metadata = AttendanceReportService.compile_attendance_report(
            company=request.company,
            params=query_params
        )

        # 3. Apply standard project pagination handlers
        paginator = StandardLimitOffsetPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request, view=self)

        # 4. Serialize rows cleanly via metadata serializers
        row_serializer = AttendanceReportRowSerializer(paginated_queryset, many=True)
        pagination_meta = PaginationAdapter.get_metadata(paginator, paginated_queryset)

        # 5. Return structured envelope layout via system standard response class
        response_payload = {
            "summary": summary,
            "filter_metadata": filter_metadata,
            "results": row_serializer.data,
            "pagination": pagination_meta
        }

        return ApiResponse.success(
            data=response_payload,
            message="Enterprise payroll attendance summaries compiled successfully.",
            status=status.HTTP_200_OK
        )