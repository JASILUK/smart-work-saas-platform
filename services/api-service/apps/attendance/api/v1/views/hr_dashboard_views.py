# apps/attendance/api/v1/views/hr_dashboard_views.py
from django.utils.dateparse import parse_date
from django.utils import timezone
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse
from rest_framework import status
from rest_framework.exceptions import ValidationError

# Core foundation boundaries & orchestration layers
from apps.attendance.services.hr_dashboard_service import HRAttendanceDashboardOrchestratorService
from apps.attendance.api.v1.serializers.hr_dashboard_serializers import HRDashboardSummaryResponseSerializer

# Core framework multi-tenant architecture imports

class HRDashboardSummaryAPIView(BaseCompanyAPIView):
    """
    Enterprise thin controller endpoint delivering the complete HR dashboard dataset.
    Tenancy isolation, authentication, billing statuses, and access privileges (RBAC) 
    are implicitly handled by the BaseCompanyAPIView permission middleware chain.
    """
    
    # Declare view permission bindings for RolePermission assessment
    required_permissions = {
        "GET": "tenant.attendance.manage",
    }

    def get(self, request, *args, **kwargs):
        # 1. request.company context is pre-populated securely by CompanyContextPermission
        company = request.company

        # 2. Extract and validate target calendar date parameters cleanly
        date_param = request.query_params.get("date")
        if date_param:
            target_date = parse_date(date_param)
            if not target_date:
                raise ValidationError("Provided date parameter format must match YYYY-MM-DD exactly.")
        else:
            target_date = timezone.now().date()

        # 3. Call your non-blocking orchestration service using the pre-resolved tenant scope
        dashboard_data = HRAttendanceDashboardOrchestratorService.compile_complete_dashboard(
            company=company,
            target_date=target_date
        )

        # 4. Serialize data payloads with optimized read pathways
        serializer = HRDashboardSummaryResponseSerializer(dashboard_data)

        # 5. Return response envelope utilizing your production static utility class
        return ApiResponse.success(
            data=serializer.data,
            message="HR Corporate metrics dashboard dataset compiled successfully.",
            status=status.HTTP_200_OK
        )