from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.core.api_response import ApiResponse
from apps.companies.api.base import BaseCompanyAPIView

from apps.attendance.selectors.daily_attendance_selector import DailyAttendanceSelector
from apps.attendance.services.daily_attendance_engine import DailyAttendanceEngine
from apps.attendance.api.v1.serializers.daily_attendance_serializer import (
    DailyAttendanceListSerializer, DailyAttendanceDetailSerializer,
    DailyAttendanceReprocessSerializer, DailyAttendanceFinalizeSerializer
)


class DailyAttendanceListAPI(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request: Request) -> Response:
        records = DailyAttendanceSelector.get_company_attendance(company=request.company, target_date=timezone.now().date())
        
        if "status" in request.query_params:
            records = records.filter(attendance_status=request.query_params["status"])
        if "membership" in request.query_params:
            records = records.filter(membership_id=request.query_params["membership"])

        serializer = DailyAttendanceListSerializer(records, many=True)
        return ApiResponse.success(data=serializer.data)


class DailyAttendanceDetailAPI(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request: Request, pk: int) -> Response:
        record = DailyAttendanceSelector.get_by_id(record_id=pk, company=request.company)
        if not record:
            return ApiResponse.error(message="Summary parameters ledger entry missing.", status=status.HTTP_404_NOT_FOUND)
        return ApiResponse.success(data=DailyAttendanceDetailSerializer(record).data)


class DailyAttendanceReprocessAPI(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request: Request) -> Response:
        serializer = DailyAttendanceReprocessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        from apps.companies.models import Membership
        target_member = Membership.objects.filter(id=serializer.validated_data["membership_id"], company=request.company).first()
        if not target_member:
            return ApiResponse.error(message="Target profile context missing.", status=status.HTTP_404_NOT_FOUND)

        try:
            record = DailyAttendanceEngine.reprocess_attendance(
                company=request.company, membership=target_member,
                target_date=serializer.validated_data["target_date"], actor=request.membership
            )
            return ApiResponse.success(data=DailyAttendanceDetailSerializer(record).data, message="Daily records recalculated successfully.")
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)


class DailyAttendanceFinalizeAPI(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request: Request) -> Response:
        serializer = DailyAttendanceFinalizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        record = DailyAttendanceSelector.get_by_id(record_id=serializer.validated_data["record_id"], company=request.company)
        if not record:
            return ApiResponse.error(message="Target summary record unmapped.", status=status.HTTP_404_NOT_FOUND)

        try:
            finalized_record = DailyAttendanceEngine.finalize_attendance(record=record, auditor=request.membership)
            return ApiResponse.success(data=DailyAttendanceDetailSerializer(finalized_record).data, message="Daily record parameter locked for payroll calculation cycles.")
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)


class DailyAttendanceReviewsAPI(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request: Request) -> Response:
        records = DailyAttendanceSelector.get_pending_reviews(company=request.company)
        serializer = DailyAttendanceListSerializer(records, many=True)
        return ApiResponse.success(data=serializer.data)