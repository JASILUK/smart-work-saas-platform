from rest_framework import serializers
from rest_framework.request import Request
from django.http import Http404

from apps.attendance.models import Shift
from apps.companies.models import Membership
from apps.attendance.selectors.shift_selector import ShiftSelector
from apps.attendance.selectors.employee_shift_assignment_selectors import EmployeeShiftAssignmentSelector
from apps.attendance.services.employee_shift_assignment_service import EmployeeShiftAssignmentService
from apps.attendance.api.v1.serializers.employee_shift_assignemnt_serializer import (
    EmployeeShiftAssignmentListSerializer,
    EmployeeShiftAssignmentDetailSerializer,
    EmployeeShiftAssignmentCreateSerializer,
    EmployeeShiftAssignmentUpdateSerializer,
)
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse


# =====================================================
# 1. EMPLOYEE SHIFT ASSIGNMENT LIST CREATE API
# =====================================================

class EmployeeShiftAssignmentListCreateAPI(BaseCompanyAPIView):
    """
    API View allowing HR administrators to query historical shift assignments 
    or register a new individual employee schedule deployment.
    """
    required_permissions = {
        "GET": "tenant.attendance.view",
        "POST": "tenant.attendance.manage",
    }

    def get(self, request: Request) -> ApiResponse:
        active_only_param = request.query_params.get("active_only")
        active_only = str(active_only_param).lower() == "true"

        # Read dataset collections entirely through the optimized Selector layer
        queryset = EmployeeShiftAssignmentSelector.list_company_assignments(
            company=request.company,
            membership_id=request.query_params.get("membership_id"),
            shift_id=request.query_params.get("shift_id"),
            active_only=active_only,
            ordering=request.query_params.get("ordering", "-effective_from"),
        )

        serializer = EmployeeShiftAssignmentListSerializer(queryset, many=True)
        return ApiResponse.success(data=serializer.data)

    def post(self, request: Request) -> ApiResponse:
        serializer = EmployeeShiftAssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        # Orchestrate the atomic service mutation layer
        assignment = EmployeeShiftAssignmentService.assign_shift(
            membership=validated_data["membership"],
            shift=validated_data["shift"],
            effective_from=validated_data["effective_from"],
            effective_until=validated_data.get("effective_until"),
            assigned_by=request.membership,
            notes=validated_data.get("notes", ""),
        )

        # Re-fetch via selector to inject pre-loaded related model structures cleanly
        assignment = EmployeeShiftAssignmentSelector.get_by_id(
            assignment_id=assignment.id, 
            company=request.company
        )
        if not assignment:
            raise Http404()

        response_serializer = EmployeeShiftAssignmentDetailSerializer(assignment)
        return ApiResponse.success(
            data=response_serializer.data,
            message="Shift assignment created.",
            status=201,
        )


# =====================================================
# 2. EMPLOYEE SHIFT ASSIGNMENT DETAIL API
# =====================================================

class EmployeeShiftAssignmentDetailAPI(BaseCompanyAPIView):
    """
    API View providing precise lookup point retrieval and safe inline 
    updates for individual worker shift tracking lines.
    """
    required_permissions = {
        "GET": "tenant.attendance.view",
        "PATCH": "tenant.attendance.manage",
    }

    def get(self, request: Request, pk: int) -> ApiResponse:
        assignment = EmployeeShiftAssignmentSelector.get_by_id(assignment_id=pk, company=request.company)
        if not assignment:
            raise Http404()

        serializer = EmployeeShiftAssignmentDetailSerializer(assignment)
        return ApiResponse.success(data=serializer.data)

    def patch(self, request: Request, pk: int) -> ApiResponse:
        assignment = EmployeeShiftAssignmentSelector.get_by_id(assignment_id=pk, company=request.company)
        if not assignment:
            raise Http404()

        serializer = EmployeeShiftAssignmentUpdateSerializer(assignment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_assignment = EmployeeShiftAssignmentService.update_assignment(
            assignment=assignment,
            validated_data=serializer.validated_data,
        )

        # Refresh state from database using the selector layer
        updated_assignment = EmployeeShiftAssignmentSelector.get_by_id(
            assignment_id=updated_assignment.id, 
            company=request.company
        )
        if not updated_assignment:
            raise Http404()

        response_serializer = EmployeeShiftAssignmentDetailSerializer(updated_assignment)
        return ApiResponse.success(
            data=response_serializer.data,
            message="Shift assignment updated.",
        )


# =====================================================
# 3. END EMPLOYEE SHIFT ASSIGNMENT API
# =====================================================

class EndEmployeeShiftAssignmentAPI(BaseCompanyAPIView):
    """
    API View applying a definitive historical closure termination threshold
    to an existing active employee timeline.
    """
    required_permissions = {
        "POST": "tenant.attendance.manage",
    }

    class InlineEndDateSerializer(serializers.Serializer):
        end_date = serializers.DateField(required=True)

    def post(self, request: Request, pk: int) -> ApiResponse:
        assignment = EmployeeShiftAssignmentSelector.get_by_id(assignment_id=pk, company=request.company)
        if not assignment:
            raise Http404()

        serializer = self.InlineEndDateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        EmployeeShiftAssignmentService.end_assignment(
            assignment=assignment,
            end_date=serializer.validated_data["end_date"],
        )

        return ApiResponse.success(message="Shift assignment ended.")


# =====================================================
# 4. DEACTIVATE EMPLOYEE SHIFT ASSIGNMENT API
# =====================================================

class DeactivateEmployeeShiftAssignmentAPI(BaseCompanyAPIView):
    """
    API View facilitating immediate workflow cancellations and administrative 
    deactivations for incorrect assignment ranges.
    """
    required_permissions = {
        "POST": "tenant.attendance.manage",
    }

    def post(self, request: Request, pk: int) -> ApiResponse:
        assignment = EmployeeShiftAssignmentSelector.get_by_id(assignment_id=pk, company=request.company)
        if not assignment:
            raise Http404()

        EmployeeShiftAssignmentService.deactivate_assignment(assignment=assignment)
        return ApiResponse.success(message="Shift assignment deactivated.")


# =====================================================
# 5. BULK ASSIGN EMPLOYEE SHIFT API
# =====================================================

class BulkAssignEmployeeShiftAPI(BaseCompanyAPIView):
    """
    API View optimized to execute batch structural roster configurations 
    across list arrays of personnel inside a unified company tenant workspace.
    """
    required_permissions = {
        "POST": "tenant.attendance.manage",
    }

    class InlineBulkAssignSerializer(serializers.Serializer):
        membership_ids = serializers.ListField(
            child=serializers.IntegerField(), required=True, allow_empty=False
        )
        shift_id = serializers.IntegerField(required=True)
        effective_from = serializers.DateField(required=True)
        effective_to = serializers.DateField(required=False, allow_null=True, default=None)
        notes = serializers.CharField(required=False, allow_blank=True, default="")

    def post(self, request: Request) -> ApiResponse:
        serializer = self.InlineBulkAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validated_data = serializer.validated_data

        # Enforce strict multi-tenant boundary compliance for target resource references
        shift = ShiftSelector.get_by_id(shift_id=validated_data["shift_id"], company=request.company)
        if not shift:
            return ApiResponse.error("The specified shift profile is invalid or inaccessible.", status=404)

        memberships = list(Membership.objects.filter(
            company=request.company,
            id__in=validated_data["membership_ids"]
        ))

        # Direct execution tracking metrics down to bulk optimization handler
        summary = EmployeeShiftAssignmentService.bulk_assign_shift(
            memberships=memberships,
            shift=shift,
            effective_from=validated_data["effective_from"],
            effective_until=validated_data.get("effective_to"),
            assigned_by=request.membership,
            notes=validated_data.get("notes", ""),
        )

        return ApiResponse.success(
            data=summary,
            message="Bulk shift assignment completed.",
        )


# =====================================================
# 6. TRANSFER EMPLOYEE SHIFT API
# =====================================================

class TransferEmployeeShiftAPI(BaseCompanyAPIView):
    """
    API View terminating an active assignment line while initializing a consecutive, 
    clean calendar deployment record to keep employee history logs gapless.
    """
    required_permissions = {
        "POST": "tenant.attendance.manage",
    }

    class InlineTransferSerializer(serializers.Serializer):
        shift_id = serializers.IntegerField(required=True)
        effective_from = serializers.DateField(required=True)
        notes = serializers.CharField(required=False, allow_blank=True, default="")

    def post(self, request: Request, pk: int) -> ApiResponse:
        assignment = EmployeeShiftAssignmentSelector.get_by_id(assignment_id=pk, company=request.company)
        if not assignment:
            raise Http404()

        serializer = self.InlineTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        validated_data = serializer.validated_data

        # Verify that the target destination shift is scoped properly inside the current company tenant
        new_shift = ShiftSelector.get_by_id(shift_id=validated_data["shift_id"], company=request.company)
        if not new_shift:
            return ApiResponse.error("The selected target shift profile is invalid or inaccessible.", status=404)

        result = EmployeeShiftAssignmentService.transfer_shift(
            assignment=assignment,
            new_shift=new_shift,
            effective_from=validated_data["effective_from"],
            assigned_by=request.membership,
            notes=validated_data.get("notes", ""),
        )

        # Eager load structural fields for the freshly instantiated assignment slice via Selector layer
        new_assignment = EmployeeShiftAssignmentSelector.get_by_id(
            assignment_id=result["new_assignment"].id, 
            company=request.company
        )
        if not new_assignment:
            raise Http404()

        response_serializer = EmployeeShiftAssignmentDetailSerializer(new_assignment)
        return ApiResponse.success(
            data=response_serializer.data,
            message="Employee transferred to new shift.",
        )