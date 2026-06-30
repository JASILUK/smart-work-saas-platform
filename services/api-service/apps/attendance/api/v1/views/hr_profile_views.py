# apps/attendance/api/v1/views/hr_profile_views.py
from rest_framework import status
# Infrastructure component targets
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse                      # Formats unified envelopes
from apps.core.standers_pagination import (
    StandardLimitOffsetPagination, 
    PaginationAdapter
)  

# Business layer bindings
from apps.attendance.services.hr_profile_service import HREmployeeProfileOrchestratorService
from apps.attendance.api.v1.serializers.hr_profile_serializers import (
    HREmployeeProfileHeaderSerializer,
    HRProfileSummaryCardsSerializer,
    HRProfileTrendChartsSerializer,
    HRProfileAttendanceRecordRowSerializer
)

class HREmployeeAttendanceProfileAPIView(BaseCompanyAPIView):
    """
    Provides fine-grained timesheet histories, period KPIs, and rolling analytics 
    for an individual employee profile view.
    """
    
    required_permissions = {
        "GET": "tenant.attendance.manage",
    }

    def get(self, request, membership_id, *args, **kwargs):
        # 1. Compile dataset through our dedicated orchestration service
        compiled_bundle = HREmployeeProfileOrchestratorService.compile_employee_profile_dataset(
            company=request.company,
            membership_id=int(membership_id),
            query_params=request.query_params.dict()
        )

        # 2. Serialize structural modules using optimized read pathways
        employee_serialized = HREmployeeProfileHeaderSerializer(compiled_bundle["employee"]).data
        summary_serialized = HRProfileSummaryCardsSerializer(compiled_bundle["summary"]).data
        charts_serialized = HRProfileTrendChartsSerializer(compiled_bundle["charts"]).data

        # 3. Apply standard limit-offset pagination configurations server-side
        paginator = StandardLimitOffsetPagination()
        paginated_records = paginator.paginate_queryset(compiled_bundle["records_queryset"], request, view=self)
        
        records_serialized = HRProfileAttendanceRecordRowSerializer(paginated_records, many=True).data
        pagination_meta = PaginationAdapter.get_metadata(paginator, paginated_records)

        # 4. Construct response graph using standard envelope formatting
        return ApiResponse.success(
            data={
                "employee": employee_serialized,
                "summary": summary_cards,
                "charts": charts_serialized,
                "records": {
                    "results": records_serialized,
                    "pagination": pagination_meta
                }
            },
            message="Granular employee attendance profile analytics compiled successfully.",
            status=status.HTTP_200_OK
        )