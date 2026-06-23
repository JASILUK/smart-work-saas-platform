from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.core.api_response import ApiResponse
from apps.companies.api.base import BaseCompanyAPIView
from apps.companies.models import Membership

from apps.attendance.models.attendance_event import AttendanceEvent
from apps.attendance.selectors.attendance_event_selector import AttendanceEventSelector
from apps.attendance.services.check_in_service import CheckInService
from apps.attendance.services.break_service import BreakService
from apps.attendance.services.check_out_service import CheckOutService
from apps.attendance.services.manual_attendance_service import ManualAttendanceService
from apps.attendance.services.live_attendance_service import LiveAttendanceService
from apps.attendance.api.v1.serializers.attendance_event_serializers import (
    AttendanceEventListSerializer, AttendanceEventDetailSerializer, 
    GenericPunchIngestionSerializer, ManualAttendanceAdjustmentSerializer
)


class AttendanceCheckInAPI(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.view"}
    
    def post(self, request: Request) -> Response:
        serializer = GenericPunchIngestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            event = CheckInService.check_in(
                company=request.company,
                membership=request.membership,
                method=serializer.validated_data["attendance_method"],
                evidence=serializer.validated_data,
                actor=request.membership
            )
            return ApiResponse.success(
                data=AttendanceEventDetailSerializer(event).data,
                message="Check-in registered successfully.",
                status=status.HTTP_201_CREATED
            )
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)


class AttendanceCheckOutAPI(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.view"}
    
    def post(self, request: Request) -> Response:
        serializer = GenericPunchIngestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            event = CheckOutService.check_out(
                company=request.company,
                membership=request.membership,
                method=serializer.validated_data["attendance_method"],
                evidence=serializer.validated_data,
                actor=request.membership
            )
            return ApiResponse.success(
                data=AttendanceEventDetailSerializer(event).data,
                message="Check-out registered successfully."
            )
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)


class AttendanceBreakOutAPI(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.view"}
    
    def post(self, request: Request) -> Response:
        serializer = GenericPunchIngestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            event = BreakService.break_out(
                company=request.company,
                membership=request.membership,
                method=serializer.validated_data["attendance_method"],
                evidence=serializer.validated_data,
                actor=request.membership
            )
            return ApiResponse.success(
                data=AttendanceEventDetailSerializer(event).data,
                message="Break interval initialized."
            )
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)


class AttendanceBreakInAPI(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.view"}
    
    def post(self, request: Request) -> Response:
        serializer = GenericPunchIngestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            event = BreakService.break_in(
                company=request.company,
                membership=request.membership,
                method=serializer.validated_data["attendance_method"],
                evidence=serializer.validated_data,
                actor=request.membership
            )
            return ApiResponse.success(
                data=AttendanceEventDetailSerializer(event).data,
                message="Returned from break interval."
            )
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)


class AttendanceEventListAPI(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request: Request) -> Response:
        records = AttendanceEvent.objects.filter(company=request.company)
        serializer = AttendanceEventListSerializer(records, many=True)
        return ApiResponse.success(data=serializer.data)


class AttendanceEventDetailAPI(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request: Request, pk: int) -> Response:
        event = AttendanceEventSelector.get_by_id(event_id=pk, company=request.company)
        if not event: return ApiResponse.error(message="Event record missing.", status=status.HTTP_404_NOT_FOUND)
        return ApiResponse.success(data=AttendanceEventDetailSerializer(event).data)


class ManualAttendanceAPI(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request: Request) -> Response:
        serializer = ManualAttendanceAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        target_member = serializer.validated_data["membership"]
        if target_member.company_id != request.company.id:
            return ApiResponse.error(message="Profile target multi-tenant mismatch.", status=status.HTTP_400_BAD_REQUEST)
            
        try:
            event = ManualAttendanceService.log_manual_action(
                company=request.company, membership=target_member,
                event_type=serializer.validated_data["event_type"],
                notes=serializer.validated_data["notes"], actor=request.membership
            )
            return ApiResponse.success(data=AttendanceEventDetailSerializer(event).data, message="Manual override record written safely.", status=status.HTTP_201_CREATED)
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)


class LiveAttendanceSummaryAPI(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request: Request) -> Response:
        summary = LiveAttendanceService.get_company_summary(company=request.company)
        return ApiResponse.success(data=summary)