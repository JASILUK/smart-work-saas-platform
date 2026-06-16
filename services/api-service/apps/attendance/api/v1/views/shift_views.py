from rest_framework.request import Request

from apps.attendance.selectors.shift_selector import ShiftSelector
from apps.attendance.services.shift_service import ShiftService
from apps.attendance.api.v1.serializers.shift_serializers import (
    ShiftListSerializer,
    ShiftDetailSerializer,
    ShiftCreateSerializer,
    ShiftUpdateSerializer,
)
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse


# =====================================================
# 1. SHIFT LIST CREATE API VIEW
# =====================================================

class ShiftListCreateAPI(BaseCompanyAPIView):
    """
    API endpoint handling collection listing and structural configuration creation
    for reusable company shift schedules inside a tenant workspace.
    """
    required_permissions = {
        "GET": "tenant.attendance.manage",
        "POST": "tenant.attendance.manage",
    }

    def get(self, request: Request) -> ApiResponse:
        """Compiles a filtered, sorted collection of company shifts."""
        is_active_param = request.query_params.get("is_active")
        is_active = (
            True if str(is_active_param).lower() == "true"
            else False if str(is_active_param).lower() == "false"
            else None
        )

        shifts_qs = ShiftSelector.list_company_shifts(
            company=request.company,
            is_active=is_active,
            shift_type=request.query_params.get("shift_type"),
            search=request.query_params.get("search"),
            ordering=request.query_params.get("ordering", "name"),
        )

        serializer = ShiftListSerializer(shifts_qs, many=True)
        return ApiResponse.success(data=serializer.data)

    def post(self, request: Request) -> ApiResponse:
        """Instantiates a new shift structure following strict tenant uniqueness rules."""
        serializer = ShiftCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        shift = ShiftService.create_shift(
            company=request.company,
            validated_data=serializer.validated_data,
        )

        # Refresh state from database using the selector layer to guarantee clean representation
        shift = ShiftSelector.get_by_id(shift_id=shift.id, company=request.company)
        
        response_serializer = ShiftDetailSerializer(shift)
        return ApiResponse.success(
            data=response_serializer.data,
            message="Shift created.",
            status=201,
        )


# =====================================================
# 2. SHIFT DETAIL API VIEW
# =====================================================

class ShiftDetailAPI(BaseCompanyAPIView):
    """
    API endpoint handling retrieval, specific detail modification, and soft deletion
    via deactivation controls for individual shift items.
    """
    required_permissions = {
        "GET": "tenant.attendance.manage",
        "PATCH": "tenant.attendance.manage",
        "DELETE": "tenant.attendance.manage",
    }

    def get(self, request: Request, public_id: int) -> ApiResponse:
        """Retrieves targeted details for a single company shift configuration."""
        shift = ShiftSelector.get_by_public_id(public_id=public_id, company=request.company)
        if not shift:
            return ApiResponse.error("Shift not found.", status=404)

        serializer = ShiftDetailSerializer(shift)
        return ApiResponse.success(data=serializer.data)

    def patch(self, request: Request, public_id: int) -> ApiResponse:
        """Modifies targeted shift configuration boundaries inline using updated fields logic."""
        shift = ShiftSelector.get_by_public_id(public_id=public_id, company=request.company)
        if not shift:
            return ApiResponse.error("Shift not found.", status=404)

        serializer = ShiftUpdateSerializer(shift, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        shift = ShiftService.update_shift(
            shift=shift,
            validated_data=serializer.validated_data,
        )

        # Re-fetch via selector to ensure all calculated and model fields map perfectly to output layout
        shift = ShiftSelector.get_by_id(shift_id=shift.id, company=request.company)

        response_serializer = ShiftDetailSerializer(shift)
        return ApiResponse.success(
            data=response_serializer.data,
            message="Shift updated.",
        )

    def delete(self, request: Request, public_id: int) -> ApiResponse:
        """Executes administrative soft deactivation rules against a target shift."""
        shift = ShiftSelector.get_by_public_id(public_id=public_id, company=request.company)
        if not shift:
            return ApiResponse.error("Shift not found.", status=404)

        ShiftService.deactivate_shift(shift=shift)
        return ApiResponse.success(message="Shift deactivated.")


# =====================================================
# 3. ACTIVATE SHIFT API VIEW
# =====================================================

class ActivateShiftAPI(BaseCompanyAPIView):
    """
    API view processing explicit reactivation tasks for legacy, seasonal, 
    or paused shift structures.
    """
    required_permissions = {
        "POST": "tenant.attendance.manage",
    }

    def post(self, request: Request, public_id: int) -> ApiResponse:
        """Restores a deactivated shift back into active roster configuration fields."""
        shift = ShiftSelector.get_by_public_id(public_id=public_id, company=request.company)
        if not shift:
            return ApiResponse.error("Shift not found.", status=404)

        ShiftService.activate_shift(shift=shift)
        return ApiResponse.success(message="Shift activated.")


# =====================================================
# 4. SET DEFAULT SHIFT API VIEW
# =====================================================

class SetDefaultShiftAPI(BaseCompanyAPIView):
    """
    API view driving global workspace rebalancing tasks by updating the 
    tenant's default structural backup work schedule.
    """
    required_permissions = {
        "POST": "tenant.attendance.manage",
    }

    def post(self, request: Request, public_id: int) -> ApiResponse:
        """Toggles company schedule configuration contexts to set a new primary default shift."""
        shift = ShiftSelector.get_by_public_id(public_id=public_id, company=request.company)
        if not shift:
            return ApiResponse.error("Shift not found.", status=404)

        shift = ShiftService.set_default_shift(shift=shift)

        # Re-fetch via selector to guarantee accurate response structural representations
        shift = ShiftSelector.get_by_id(shift_id=shift.id, company=request.company)

        response_serializer = ShiftDetailSerializer(shift)
        return ApiResponse.success(
            data=response_serializer.data,
            message="Default shift updated.",
        )