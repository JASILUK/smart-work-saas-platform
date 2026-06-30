from typing import Any

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils.dateparse import parse_date

# Core framework boundaries
from apps.attendance.selectors.hr_management_selector import HRAttendanceManagementSelector
from apps.attendance.services.hr_management_service import HRAttendanceManagementService
from apps.attendance.validators.hr_foundation_validator import HRFoundationValidator
from apps.attendance.api.v1.serializers.hr_serializers import (
    HRDailyLedgerOutputSerializer,
    HRRecordDetailResponseSerializer,
    HRManualPunchInjectionSerializer,
    HRStandardActionPayloadSerializer
)

class HRBaseAPIView(APIView):
    """
    Base API View that centralizes core tenant context parsing and security checks.
    """
    permission_classes = [IsAuthenticated]

    def get_validated_context(self, request) -> tuple:
        company = HRFoundationValidator.validate_company_context(getattr(request, "company", None))
        admin_actor = HRFoundationValidator.validate_administrative_actor(request.user, company)
        return company, admin_actor

    def send_response(self, status_code: int, message: str, data: Any = None, errors: Any = None) -> Response:
        """
        Maintains structural compatibility with your existing ApiResponse configuration rules.
        """
        return Response({
            "status": "success" if status_code < 400 else "error",
            "message": message,
            "data": data,
            "errors": errors
        }, status=status_code)

class HRDashboardSummaryAPIView(HRBaseAPIView):
    def get(self, request, *args, **kwargs):
        company, _ = self.get_validated_context(request)
        
        date_param = request.query_params.get("date")
        target_date = parse_date(date_param) if date_param else timezone.now().date()
        
        if not target_date:
            return self.send_response(status.HTTP_400_BAD_REQUEST, "Invalid format provided for date parameter.")
            
        summary_data = HRAttendanceManagementSelector.get_aggregated_dashboard_summary(
            company=company, target_date=target_date
        )
        return self.send_response(status.HTTP_200_OK, "Dashboard summary calculated successfully.", data=summary_data)

class HRCompanyLedgerAPIView(HRBaseAPIView):
    def get(self, request, *args, **kwargs):
        company, _ = self.get_validated_context(request)
        
        # Parse query parameters safely
        date_from = parse_date(request.query_params.get("date_from", ""))
        date_to = parse_date(request.query_params.get("date_to", ""))
        status_filter = request.query_params.get("status")
        dept_id = request.query_params.get("department_id")
        search_query = request.query_params.get("search")
        
        review_req = request.query_params.get("review_required")
        review_bool = review_req.lower() == "true" if review_req else None
        
        ledger_qs = HRAttendanceManagementSelector.list_daily_attendance_ledger(
            company=company,
            date_from=date_from,
            date_to=date_to,
            status=status_filter,
            department_id=int(dept_id) if dept_id else None,
            review_required=review_bool,
            search_query=search_query
        )
        
        # Use our optimized serializer layer to process data lists efficiently
        serializer = HRDailyLedgerOutputSerializer(ledger_qs, many=True)
        return self.send_response(status.HTTP_200_OK, "Company attendance ledger loaded.", data={"results": serializer.data})

class HRRecordDetailAPIView(HRBaseAPIView):
    def get(self, request, record_id, *args, **kwargs):
        company, _ = self.get_validated_context(request)
        
        record = HRAttendanceManagementSelector.get_base_hr_queryset(company=company).filter(id=record_id).first()
        HRFoundationValidator.validate_record_operational_state(record)
        
        serializer = HRRecordDetailResponseSerializer(record)
        return self.send_response(status.HTTP_200_OK, "Detailed timesheet graph traced successfully.", data=serializer.data)

class HRRecordFinalizeAPIView(HRBaseAPIView):
    def post(self, request, record_id, *args, **kwargs):
        company, admin_actor = self.get_validated_context(request)
        
        serializer = HRStandardActionPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        record = HRAttendanceManagementService.finalize_record(
            company=company,
            admin_actor=admin_actor,
            record_id=record_id,
            reason=serializer.validated_data["reason"]
        )
        return self.send_response(status.HTTP_200_OK, f"Timesheet ledger row #{record.id} finalized successfully.")

class HRRecordUnlockAPIView(HRBaseAPIView):
    def post(self, request, record_id, *args, **kwargs):
        company, admin_actor = self.get_validated_context(request)
        
        serializer = HRStandardActionPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        record = HRAttendanceManagementService.unlock_record(
            company=company,
            admin_actor=admin_actor,
            record_id=record_id,
            reason=serializer.validated_data["reason"]
        )
        return self.send_response(status.HTTP_200_OK, f"Timesheet ledger row #{record.id} opened for revisions.")

class HRRecordReprocessAPIView(HRBaseAPIView):
    def post(self, request, record_id, *args, **kwargs):
        company, admin_actor = self.get_validated_context(request)
        
        serializer = HRStandardActionPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        record = HRAttendanceManagementService.reprocess_record_timeline(
            company=company,
            admin_actor=admin_actor,
            record_id=record_id,
            reason=serializer.validated_data["reason"]
        )
        return self.send_response(status.HTTP_200_OK, f"Calculations updated for record entry #{record.id}.")

class HRManualCorrectionAPIView(HRBaseAPIView):
    def post(self, request, *args, **kwargs):
        company, admin_actor = self.get_validated_context(request)
        
        serializer = HRManualPunchInjectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        target_employee = HRFoundationValidator.validate_target_employee(
            serializer.validated_data["membership_id"], company
        )
        
        event = HRAttendanceManagementService.inject_manual_correction_event(
            company=company,
            admin_actor=admin_actor,
            target_member=target_employee,
            data=serializer.validated_data
        )
        return self.send_response(status.HTTP_201_CREATED, f"Manual correction action committed under token lookup reference ID: {event.id}.")