from rest_framework import status
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse


from apps.attendance.services.employee_dashboard_service import EmployeeDashboardService
from apps.attendance.api.v1.serializers.employee_dashboard_serializer import EmployeeDashboardSerializer

class EmployeeDashboardAPIView(BaseCompanyAPIView):
    """
    Unified operational gateway compiling analytics data structures, guardrails parameters, 
    and punch action items for the caller profile scope.
    """
    required_permissions = {
        "GET": "tenant.attendance.view"
    }

    def get(self, request, *args, **kwargs):
        # Service-Layer Isolation Orchestration
        dashboard_data = EmployeeDashboardService.get_dashboard(
            company=request.company,
            membership=request.membership
        )

        # Output Serializer Structure Enforcement
        serializer = EmployeeDashboardSerializer(dashboard_data)

        # 2. Return the serialized representation data dictionary safely
        return ApiResponse.success(
            data=serializer.data,
            message="Employee attendance dashboard telemetry consolidated safely.",
            status=status.HTTP_200_OK
        )