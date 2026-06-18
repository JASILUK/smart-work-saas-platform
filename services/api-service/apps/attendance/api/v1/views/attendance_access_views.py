from apps.attendance.models.attendance_access_rule import AttendanceAccessRule
from apps.attendance.models.employee_attendance_override import EmployeeAttendanceOverride
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.core.api_response import ApiResponse
from apps.companies.api.base import BaseCompanyAPIView
from apps.companies.models import Membership

# Selector & Service layers imports
from apps.attendance.selectors.company_attendance_default_selector import CompanyAttendanceDefaultSelector
from apps.attendance.selectors.attendance_access_rule_selector import AttendanceAccessRuleSelector
from apps.attendance.selectors.employee_attendance_override_selector import EmployeeAttendanceOverrideSelector
from apps.attendance.services.company_attendance_default_service import CompanyAttendanceDefaultService
from apps.attendance.services.attendance_access_rule_service import AttendanceAccessRuleService
from apps.attendance.services.employee_attendance_override_service import EmployeeAttendanceOverrideService
from apps.attendance.services.attendance_access_resolver_service import AttendanceAccessResolverService

# Serializers layer imports
from apps.attendance.api.v1.serializers.attendance_access_serializers import (
    CompanyAttendanceDefaultDetailSerializer, CompanyAttendanceDefaultCreateSerializer,
    AttendanceAccessRuleListSerializer, AttendanceAccessRuleDetailSerializer, AttendanceAccessRuleCreateSerializer,
    EmployeeAttendanceOverrideListSerializer, EmployeeAttendanceOverrideDetailSerializer, EmployeeAttendanceOverrideCreateSerializer,
    AttendanceAccessResolutionSerializer
)


class CompanyAttendanceDefaultAPI(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view", "POST": "tenant.attendance.manage", "PATCH": "tenant.attendance.manage"}

    def get(self, request: Request) -> Response:
        instance = CompanyAttendanceDefaultSelector.get_active_default(company=request.company)
        if not instance:
            return ApiResponse.success(data=None, message="No corporate configuration initialized.")
        return ApiResponse.success(data=CompanyAttendanceDefaultDetailSerializer(instance).data)

    def post(self, request: Request) -> Response:
        serializer = CompanyAttendanceDefaultCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            instance = CompanyAttendanceDefaultService.create_default(
                company=request.company,
                method_ids=[m.id for m in serializer.validated_data.get("allowed_methods", [])],
                location_ids=[l.id for l in serializer.validated_data.get("allowed_locations", [])],
                validation_mode=serializer.validated_data.get("validation_mode"),
                is_active=serializer.validated_data.get("is_active", True)
            )
            return ApiResponse.success(data=CompanyAttendanceDefaultDetailSerializer(instance).data, status=status.HTTP_201_CREATED)
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)

    def patch(self, request: Request) -> Response:
        instance = getattr(request.company, 'attendance_default', None)
        if not instance:
            return ApiResponse.error(message="No corporate default targets found to patch.", status=status.HTTP_404_NOT_FOUND)
        serializer = CompanyAttendanceDefaultCreateSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            updated_instance = CompanyAttendanceDefaultService.update_default(instance=instance, validated_data=serializer.validated_data)
            return ApiResponse.success(data=CompanyAttendanceDefaultDetailSerializer(updated_instance).data)
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)


class AttendanceAccessRuleListCreateAPI(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view", "POST": "tenant.attendance.manage"}

    def get(self, request: Request) -> Response:
        rules = AttendanceAccessRuleSelector.list_company_rules(company=request.company)
        return ApiResponse.success(data=AttendanceAccessRuleListSerializer(rules, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = AttendanceAccessRuleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            rule = AttendanceAccessRuleService.create_rule(company=request.company, validated_data=serializer.validated_data)
            return ApiResponse.success(data=AttendanceAccessRuleDetailSerializer(rule).data, status=status.HTTP_201_CREATED)
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)


class AttendanceAccessRuleDetailAPI(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view", "PATCH": "tenant.attendance.manage", "DELETE": "tenant.attendance.manage"}

    def _get_rule(self, request, rule_id):
        return AttendanceAccessRule.objects.filter(id=rule_id, company=request.company).first()

    def get(self, request: Request, rule_id: int) -> Response:
        rule = self._get_rule(request, rule_id)
        if not rule: return ApiResponse.error(message="Access rule not found.", status=status.HTTP_404_NOT_FOUND)
        return ApiResponse.success(data=AttendanceAccessRuleDetailSerializer(rule).data)

    def patch(self, request: Request, rule_id: int) -> Response:
        rule = self._get_rule(request, rule_id)
        if not rule: return ApiResponse.error(message="Access rule not found.", status=status.HTTP_404_NOT_FOUND)
        serializer = AttendanceAccessRuleCreateSerializer(rule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            updated_rule = AttendanceAccessRuleService.update_rule(instance=rule, validated_data=serializer.validated_data)
            return ApiResponse.success(data=AttendanceAccessRuleDetailSerializer(updated_rule).data)
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)

    def delete(self, request: Request, rule_id: int) -> Response:
        rule = self._get_rule(request, rule_id)
        if not rule: return ApiResponse.error(message="Access rule not found.", status=status.HTTP_404_NOT_FOUND)
        AttendanceAccessRuleService.update_rule(instance=rule, validated_data={"is_active": False})
        return ApiResponse.success(message="Attendance access rule soft-deactivated successfully.")


class EmployeeAttendanceOverrideListCreateAPI(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view", "POST": "tenant.attendance.manage"}

    def get(self, request: Request) -> Response:
        overrides = EmployeeAttendanceOverride.objects.filter(company=request.company)
        return ApiResponse.success(data=EmployeeAttendanceOverrideListSerializer(overrides, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = EmployeeAttendanceOverrideCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            override = EmployeeAttendanceOverrideService.create_override(
                company=request.company,
                membership=serializer.validated_data.get("membership"),
                validated_data=serializer.validated_data
            )
            return ApiResponse.success(data=EmployeeAttendanceOverrideDetailSerializer(override).data, status=status.HTTP_201_CREATED)
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)


class EmployeeAttendanceOverrideDetailAPI(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view", "PATCH": "tenant.attendance.manage", "DELETE": "tenant.attendance.manage"}

    def _get_override(self, request, override_id):
        return EmployeeAttendanceOverride.objects.filter(id=override_id, company=request.company).first()

    def get(self, request: Request, override_id: int) -> Response:
        override = self._get_override(request, override_id)
        if not override: return ApiResponse.error(message="Exception profile not found.", status=status.HTTP_404_NOT_FOUND)
        return ApiResponse.success(data=EmployeeAttendanceOverrideDetailSerializer(override).data)

    def patch(self, request: Request, override_id: int) -> Response:
        override = self._get_override(request, override_id)
        if not override: return ApiResponse.error(message="Exception profile not found.", status=status.HTTP_404_NOT_FOUND)
        serializer = EmployeeAttendanceOverrideCreateSerializer(override, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            updated_override = EmployeeAttendanceOverrideService.update_override(instance=override, validated_data=serializer.validated_data)
            return ApiResponse.success(data=EmployeeAttendanceOverrideDetailSerializer(updated_override).data)
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)

    def delete(self, request: Request, override_id: int) -> Response:
        override = self._get_override(request, override_id)
        if not override: return ApiResponse.error(message="Exception profile not found.", status=status.HTTP_404_NOT_FOUND)
        EmployeeAttendanceOverrideService.remove_override(instance=override)
        return ApiResponse.success(message="Employee individual exception record purged successfully.")


class AttendanceAccessResolutionAPI(BaseCompanyAPIView):
    """
    Evaluates real-time clearance tracking limits for an employee context.
    """
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request: Request) -> Response:
        membership_id = request.query_params.get("membership_id")
        if not membership_id:
            return ApiResponse.error(message="Parameter field 'membership_id' is required.", status=status.HTTP_400_BAD_REQUEST)

        membership = Membership.objects.filter(id=membership_id, company=request.company).first()
        if not membership:
            return ApiResponse.error(message="Target user profile record not found inside this company context.", status=status.HTTP_404_NOT_FOUND)

        try:
            resolution_data = AttendanceAccessResolverService.resolve_access(company=request.company, membership=membership)
            serializer = AttendanceAccessResolutionSerializer(resolution_data)
            return ApiResponse.success(data=serializer.data)
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message, status=status.HTTP_400_BAD_REQUEST)