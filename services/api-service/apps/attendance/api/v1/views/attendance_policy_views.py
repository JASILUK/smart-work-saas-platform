from rest_framework import status
from rest_framework.request import Request

from apps.attendance.selectors.attendance_policy_selector import AttendancePolicySelector
from apps.attendance.services.attendance_policy_service import AttendancePolicyService
from apps.attendance.api.v1.serializers.attendance_policy_serializers import (
    AttendancePolicySerializer,
    AttendancePolicyUpdateSerializer,
)
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse


# =====================================================
# 1. ATTENDANCE POLICY DETAIL API VIEW
# =====================================================

class AttendancePolicyDetailAPI(BaseCompanyAPIView):
    """
    API View allowing authorized users to inspect the current company tenant's 
    attendance policy rules. 
    
    If no policy has been instantiated yet for the tenant workspace, it triggers 
    an automatic fallback initialization flow to prevent analytical execution gaps.
    """
    required_permissions = {
        "GET": "tenant.attendance.view",
    }

    # =====================================================
    # GET
    # =====================================================

    def get(self, request: Request) -> ApiResponse:
        """Retrieves or instantiates the active workspace interpretation profile."""
        policy = AttendancePolicySelector.get_by_company(company=request.company)
        
        if not policy:
            # Atomic default initialization fall-through layer
            policy = AttendancePolicyService.get_or_create_default_policy(company=request.company)

        serializer = AttendancePolicySerializer(policy)
        return ApiResponse.success(data=serializer.data)


# =====================================================
# 2. ATTENDANCE POLICY UPDATE API VIEW
# =====================================================

class AttendancePolicyUpdateAPI(BaseCompanyAPIView):
    """
    API View driving partial, patch-based parameter mutations against the company 
    attendance policy configuration matrix.
    """
    required_permissions = {
        "PATCH": "tenant.attendance.manage",
    }

    # =====================================================
    # PATCH
    # =====================================================

    def patch(self, request: Request) -> ApiResponse:
        """Validates incoming thresholds and updates the company interpretation metrics."""
        policy = AttendancePolicyService.get_or_create_default_policy(company=request.company)

        serializer = AttendancePolicyUpdateSerializer(
            instance=policy,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        updated_policy = AttendancePolicyService.update_policy(
            company=request.company,
            validated_data=serializer.validated_data,
        )

        response_serializer = AttendancePolicySerializer(updated_policy)
        return ApiResponse.success(
            data=response_serializer.data,
            message="Attendance policy updated.",
        )


# =====================================================
# 3. ATTENDANCE POLICY RESET API VIEW
# =====================================================

class AttendancePolicyResetAPI(BaseCompanyAPIView):
    """
    API View executing administrative recovery protocols by reverting 
    customized tenant threshold criteria back to baseline corporate system defaults.
    """
    required_permissions = {
        "POST": "tenant.attendance.manage",
    }

    # =====================================================
    # POST
    # =====================================================

    def post(self, request: Request) -> ApiResponse:
        """Wipes localized override matrices and restores standard model defaults."""
        updated_policy = AttendancePolicyService.reset_to_defaults(company=request.company)

        response_serializer = AttendancePolicySerializer(updated_policy)
        return ApiResponse.success(
            data=response_serializer.data,
            message="Attendance policy reset to defaults.",
        )