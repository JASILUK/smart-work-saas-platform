# apps/attendance/api/v1/views/hr_directory_views.py
from django.utils.dateparse import parse_date
from django.utils import timezone
from rest_framework import status

# Core layer business abstractions
from apps.attendance.services.hr_directory_service import HREmployeeDirectoryService
from apps.attendance.api.v1.serializers.hr_directory_serializers import HREmployeeDirectoryRowSerializer

# Framework structural component dependencies
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse                      # Formats unified envelopes
from apps.core.standers_pagination import (
    StandardLimitOffsetPagination, 
    PaginationAdapter
)                                                                  # Enterprise standard list workflows

class HREmployeeAttendanceDirectoryAPIView(BaseCompanyAPIView):
    """
    Enterprise-grade endpoint exposing the company-wide daily Employee Attendance Directory grid.
    Tenancy context parsing, subscription status checks, and access control authorizations (RBAC)
    are handled automatically by the base view class hierarchy layers.
    """
    
    # Enforce standard role permission checks via RolePermission
    required_permissions = {
        "GET": "tenant.attendance.manage",
    }

    def get(self, request, *args, **kwargs):
        query_params = request.query_params.dict()
        
        # 1. Enforce current calendar date as system fallback baseline if parameters are blank
        if "date" not in query_params or not query_params["date"]:
            query_params["date"] = str(timezone.now().date())
        else:
            if not parse_date(query_params["date"]):
                return ApiResponse.error(
                    message="Target date parameter format must match YYYY-MM-DD exactly.", 
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 2. Delegate query filtering, corporate search, and sorting directly to your service
        directory_queryset = HREmployeeDirectoryService.compile_directory_dataset(
            company=request.company,
            params=query_params
        )

        # 3. Initialize your enterprise standard paginator class instance
        paginator = StandardLimitOffsetPagination()
        
        # 4. Generate the page-wrapped slice array block server-side
        paginated_queryset = paginator.paginate_queryset(directory_queryset, request, view=self)

        # 5. Serialize data arrays using highly optimized annotated read fields
        serializer = HREmployeeDirectoryRowSerializer(paginated_queryset, many=True)
        
        # 6. Extract unified tracking indicators using your custom adapter layout
        pagination_meta = PaginationAdapter.get_metadata(paginator, paginated_queryset)

        # 7. Deliver clean structural payload using your ApiResponse static helper
        return ApiResponse.success(
            data={
                "results": serializer.data,
                "pagination": pagination_meta
            },
            message="Employee attendance directory dataset compiled successfully.",
            status=status.HTTP_200_OK
        )