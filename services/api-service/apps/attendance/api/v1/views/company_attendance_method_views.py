from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from apps.core.api_response import ApiResponse  # Centralized project standard API response constructor
from apps.companies.api.base import BaseCompanyAPIView

from apps.attendance.selectors.company_attendance_method_selector import CompanyAttendanceMethodSelector
from apps.attendance.services.company_attendance_method_service import CompanyAttendanceMethodService
from apps.attendance.api.v1.serializers.company_attendance_method_serializers import (
    CompanyAttendanceMethodDetailSerializer,
    CompanyAttendanceMethodReplaceSerializer,
)


class CompanyAttendanceMethodAPI(BaseCompanyAPIView):
    """
    Command Center interface managing available validation channels per workspace.
    Coordinating ingestion frameworks globally for a Company context.
    """

    required_permissions = {
        "GET": "tenant.attendance.view",
        "PUT": "tenant.attendance.manage",
    }

    def get(self, request: Request) -> Response:
        """
        Lists all active methods deployed in the company context.
        """
        company = request.company  # Automatically resolved by BaseCompanyAPIView context
        methods_queryset = CompanyAttendanceMethodSelector.get_company_methods(company=company)
        
        serializer = CompanyAttendanceMethodDetailSerializer(methods_queryset, many=True)
        return ApiResponse.success(data=serializer.data)

    def put(self, request: Request) -> Response:
        """
        Replaces and synchronizes the active company configurations with a new list of tracking methods.
        """
        company = request.company
        actor = request.membership  # Resolves tracking metadata context hooks cleanly
        
        serializer = CompanyAttendanceMethodReplaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        target_methods = serializer.validated_data["methods"]
        
        updated_records = CompanyAttendanceMethodService.replace_methods(
            company=company,
            methods=target_methods,
            actor=actor
        )
        
        response_serializer = CompanyAttendanceMethodDetailSerializer(updated_records, many=True)
        return ApiResponse.success(
            data=response_serializer.data,
            message="Attendance methods updated successfully.",
            status=status.HTTP_200_OK
        )


class CompanyAttendanceMethodActionAPI(BaseCompanyAPIView):
    """
    Handles focused, individual method mutations (Enable and Soft-Deactivate)
    via explicit path targeting endpoints.
    """
    
    required_permissions = {
        "POST": "tenant.attendance.manage",
        "DELETE": "tenant.attendance.manage",
    }

    def post(self, request: Request, method_name: str) -> Response:
        """
        POST /attendance/methods/<method_name>/enable/
        Idempotently activates or overrides a specific tracking method channel.
        """
        company = request.company
        actor = request.membership
        method_upper = method_name.strip().upper()

        record = CompanyAttendanceMethodService.enable_method(
            company=company,
            method=method_upper,
            actor=actor
        )
        serializer = CompanyAttendanceMethodDetailSerializer(record)
        return ApiResponse.success(
            data=serializer.data,
            message=f"Attendance method '{method_upper}' enabled successfully."
        )

    def delete(self, request: Request, method_name: str) -> Response:
        """
        DELETE /attendance/methods/<method_name>/
        Executes a safe soft-delete operation by shifting 'is_active' to False.
        """
        company = request.company
        actor = request.membership
        method_upper = method_name.strip().upper()

        # Business Rule 1 Check: Ensure at least one active channel remains
        active_methods = CompanyAttendanceMethodSelector.get_company_methods(company=company)
        if active_methods.count() <= 1 and CompanyAttendanceMethodSelector.is_method_enabled(company, method_upper):
            return ApiResponse.error(
                message="Operation aborted. At least one active attendance verification channel must remain active.",
                status=status.HTTP_400_BAD_REQUEST
            )

        CompanyAttendanceMethodService.disable_method(
            company=company,
            method=method_upper,
            actor=actor
        )
        
        return ApiResponse.success(
            message=f"Attendance method '{method_upper}' deactivated and soft-deleted safely.",
            status=status.HTTP_200_OK
        )