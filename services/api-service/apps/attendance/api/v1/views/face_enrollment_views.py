from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.core.api_response import ApiResponse
from apps.companies.api.base import BaseCompanyAPIView
from apps.companies.models import Membership

from apps.attendance.selectors.face_enrollment_selector import FaceEnrollmentSelector
from apps.attendance.selectors.company_face_policy_selector import CompanyFaceEnrollmentPolicySelector
from apps.attendance.services.company_face_policy_service import CompanyFaceEnrollmentPolicyService
from apps.attendance.services.face_enrollment_service import FaceEnrollmentService
from apps.attendance.api.v1.serializers.face_enrollment_serializers import (
    CompanyFaceEnrollmentPolicyDetailSerializer, CompanyFaceEnrollmentPolicyCreateSerializer, CompanyFaceEnrollmentPolicyUpdateSerializer,
    FaceEnrollmentListSerializer, FaceEnrollmentDetailSerializer, FaceEnrollmentCreateSerializer,
    FaceEnrollmentRejectSerializer, FaceEnrollmentRevokeSerializer
)


class CompanyFaceEnrollmentPolicyAPI(BaseCompanyAPIView):
    """
    Enterprise Orchestration Router managing tenant facial recognition registration guardrails.
    """
    required_permissions = {
        "GET": "tenant.attendance.view", 
        "POST": "tenant.attendance.manage", 
        "PATCH": "tenant.attendance.manage",
        "DELETE": "tenant.attendance.manage"
    }

    def get(self, request: Request) -> Response:
        """
        Returns the currently active biometric setup policy configuration.
        """
        instance = CompanyFaceEnrollmentPolicySelector.get_company_policy(company=request.company)
        if not instance:
            return ApiResponse.success(data=None)
            
        return ApiResponse.success(data=CompanyFaceEnrollmentPolicyDetailSerializer(instance).data)

    def post(self, request: Request) -> Response:
        """
        Creates the initial baseline face policy. Throws an error if an active setup exists.
        """
        # Read operations must strictly run through selectors
        existing_policy = CompanyFaceEnrollmentPolicySelector.get_active_policy(company=request.company)
        if existing_policy:
            return ApiResponse.error(
                message="Face enrollment policy already exists. Use PATCH instead.",
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = CompanyFaceEnrollmentPolicyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        policy = CompanyFaceEnrollmentPolicyService.create_policy(
            company=request.company,
            policy_type=serializer.validated_data["policy_type"],
            is_active=serializer.validated_data.get("is_active", True)
        )
        return ApiResponse.success(
            data=CompanyFaceEnrollmentPolicyDetailSerializer(policy).data, 
            status=status.HTTP_201_CREATED
        )

    def patch(self, request: Request) -> Response:
        """
        Partially updates operational attributes on the tenant's policy rule instance.
        """
        policy = CompanyFaceEnrollmentPolicySelector.get_company_policy(company=request.company)
        if not policy:
            return ApiResponse.error(
                message="Face enrollment policy not found.",
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = CompanyFaceEnrollmentPolicyUpdateSerializer(policy, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_policy = CompanyFaceEnrollmentPolicyService.update_policy(
            instance=policy,
            validated_data=serializer.validated_data
        )
        return ApiResponse.success(data=CompanyFaceEnrollmentPolicyDetailSerializer(updated_policy).data)

    def delete(self, request: Request) -> Response:
        """
        Executes a soft deactivation on the active biometric enrollment policy corporate-wide.
        """
        policy = CompanyFaceEnrollmentPolicySelector.get_active_policy(company=request.company)
        if not policy:
            return ApiResponse.error(
                message="Face enrollment policy not found.",
                status=status.HTTP_404_NOT_FOUND
            )

        CompanyFaceEnrollmentPolicyService.deactivate_policy(instance=policy)
        return ApiResponse.success(message="Face enrollment policy deactivated successfully.")
    

class EmployeeSelfEnrollmentAPI(BaseCompanyAPIView):
    # Restricts calls to authenticated memberships active inside the target company context
    required_permissions = {"POST": "tenant.attendance.view"}

    def post(self, request: Request) -> Response:
        serializer = FaceEnrollmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            enrollment = FaceEnrollmentService.submit_self_enrollment(
                company=request.company,
                membership=request.membership,  # Evaluates caller context
                embedding=serializer.validated_data["embedding"]
            )
            return ApiResponse.success(
                data=FaceEnrollmentDetailSerializer(enrollment).data,
                message="Biometric face enrollment submitted successfully.",
                status=status.HTTP_201_CREATED
            )
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)


class HRInstructionEnrollmentAPI(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request: Request) -> Response:
        target_membership_id = request.data.get("membership_id")
        if not target_membership_id:
            return ApiResponse.error(message="Required argument 'membership_id' is missing.", status=status.HTTP_400_BAD_REQUEST)

        target_member = Membership.objects.filter(id=target_membership_id, company=request.company).first()
        if not target_member:
            return ApiResponse.error(message="Target employee workspace record not found.", status=status.HTTP_404_NOT_FOUND)

        serializer = FaceEnrollmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            enrollment = FaceEnrollmentService.hr_enroll_employee(
                company=request.company,
                target_membership=target_member,
                actor=request.membership,
                embedding=serializer.validated_data["embedding"]
            )
            return ApiResponse.success(
                data=FaceEnrollmentDetailSerializer(enrollment).data,
                message="Employee biometric profile explicitly configured and approved by HR.",
                status=status.HTTP_201_CREATED
            )
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)


class FaceEnrollmentListAPI(BaseCompanyAPIView):
    """
    Multi-tenant endpoint for monitoring biometric profile queues.
    - Managers view all records within the tenant company boundary.
    - Regular employees are strictly locked to their own profiles.
    """
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request: Request) -> Response:
        company = request.company
        caller_membership = request.membership

        # Check if the caller has corporate administrative privileges
        has_manage_privilege = caller_membership.role.permissions.filter(
            code="tenant.attendance.manage"
        ).exists()

        if has_manage_privilege:
            # Case 1: Manager evaluation scope. Apply administrative filters out of query parameters.
            records = FaceEnrollmentSelector.list_company_enrollments(company=company)
            
            if "status" in request.query_params:
                records = records.filter(status=request.query_params["status"])
            if "membership" in request.query_params:
                records = records.filter(membership_id=request.query_params["membership"])
            if "source" in request.query_params:
                records = records.filter(enrollment_source=request.query_params["source"])
        else:
            # Case 2: Employee self-service view scope. Force isolation to the caller's membership record.
            # Explicitly drops query parameter filters to block membership query parameters abuse.
            records = FaceEnrollmentSelector.list_company_enrollments(
                company=company, 
                membership=caller_membership
            )

        return ApiResponse.success(data=FaceEnrollmentListSerializer(records, many=True).data)


class FaceEnrollmentDetailAPI(BaseCompanyAPIView):
    """
    Multi-tenant details view endpoint for isolating specific record identifiers.
    - Prevents cross-employee biometric footprint leakage using stealth 404 responses.
    """
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request: Request, pk: int) -> Response:
        company = request.company
        caller_membership = request.membership

        has_manage_privilege = caller_membership.role.permissions.filter(
            code="tenant.attendance.manage"
        ).exists()

        if has_manage_privilege:
            # Managers can trace any object key inside their tenant partition
            record = FaceEnrollmentSelector.get_by_id(enrollment_id=pk, company=company)
        else:
            # Regular employees can only track their own record instances.
            # If the record belongs to another worker, it falls back to a 404 to block ID guessing.
            record = FaceEnrollmentSelector.get_by_id(
                enrollment_id=pk, 
                company=company, 
                membership=caller_membership
            )

        if not record:
            return ApiResponse.error(
                message="Face enrollment tracking profile not found.", 
                status=status.HTTP_404_NOT_FOUND
            )

        return ApiResponse.success(data=FaceEnrollmentDetailSerializer(record).data)


class FaceEnrollmentApproveAPI(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request: Request, pk: int) -> Response:
        record = FaceEnrollmentSelector.get_by_id(enrollment_id=pk, company=request.company)
        if not record: return ApiResponse.error(message="Record not found.", status=status.HTTP_404_NOT_FOUND)
        try:
            FaceEnrollmentService.approve_enrollment(enrollment=record, actor=request.membership)
            return ApiResponse.success(message="Biometric profile enrollment successfully approved and activated.")
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)


class FaceEnrollmentRejectAPI(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request: Request, pk: int) -> Response:
        record = FaceEnrollmentSelector.get_by_id(enrollment_id=pk, company=request.company)
        if not record: return ApiResponse.error(message="Record not found.", status=status.HTTP_404_NOT_FOUND)
        serializer = FaceEnrollmentRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            FaceEnrollmentService.reject_enrollment(enrollment=record, actor=request.membership, reason=serializer.validated_data["reason"])
            return ApiResponse.success(message="Biometric profile enrollment request rejected.")
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)


class FaceEnrollmentRevokeAPI(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request: Request, pk: int) -> Response:
        record = FaceEnrollmentSelector.get_by_id(enrollment_id=pk, company=request.company)
        if not record: return ApiResponse.error(message="Record not found.", status=status.HTTP_404_NOT_FOUND)
        serializer = FaceEnrollmentRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            FaceEnrollmentService.revoke_enrollment(enrollment=record, actor=request.membership, reason=serializer.validated_data["reason"])
            return ApiResponse.success(message="Active biometric profile revoked and deactivated successfully.")
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)