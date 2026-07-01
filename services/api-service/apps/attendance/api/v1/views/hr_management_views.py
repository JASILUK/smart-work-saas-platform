import datetime
from typing import Any
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status

# Core framework multi-tenant architecture & response components
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse         # Extends standardized project success/error envelopes

# Core business domain layers
from apps.attendance.selectors.hr_management_selector import HRAttendanceManagementSelector
from apps.attendance.services.hr_management_service import HRAttendanceManagementService
from apps.attendance.validators.hr_foundation_validator import HRFoundationValidator
from apps.attendance.api.v1.serializers.hr_serializers import (
    HRDailyLedgerOutputSerializer,
    HRRecordDetailResponseSerializer,
    HRManualPunchInjectionSerializer,
    HRStandardActionPayloadSerializer
)

class HRDashboardSummaryAPIView(BaseCompanyAPIView):
    """
    Enterprise thin controller endpoint delivering the complete HR dashboard dataset summary.
    """
    required_permissions = {
        "GET": "tenant.attendance.view",
    }

    def get(self, request, *args, **kwargs):
        # request.company is pre-populated securely by your Permission Classes layer
        company = request.company
        
        date_param = request.query_params.get("date")
        target_date = parse_date(date_param) if date_param else timezone.now().date()
        
        if not target_date:
            return ApiResponse.error(message="Invalid format provided for date parameter.", status=status.HTTP_400_BAD_REQUEST)
            
        summary_data = HRAttendanceManagementSelector.get_aggregated_dashboard_summary(
            company=company, target_date=target_date
        )
        return ApiResponse.success(data=summary_data, message="Dashboard summary calculated successfully.")


class HRCompanyLedgerAPIView(BaseCompanyAPIView):
    """
    Provides collection listings for the high-scale corporate daily attendance review grid.
    """
    required_permissions = {
        "GET": "tenant.attendance.view",
    }

    def get(self, request, *args, **kwargs):
        company = request.company
        
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
        
        serializer = HRDailyLedgerOutputSerializer(ledger_qs, many=True)
        return ApiResponse.success(data={"results": serializer.data}, message="Company attendance ledger loaded.")


class HRRecordDetailAPIView(BaseCompanyAPIView):
    """
    Exposes detailed single-day time sheet summary graphs and transactional child rows.
    """
    required_permissions = {
        "GET": "tenant.attendance.view",
    }

    def get(self, request, record_id, *args, **kwargs):
        company = request.company
        
        record = HRAttendanceManagementSelector.get_base_hr_queryset(company=company).filter(id=record_id).first()
        HRFoundationValidator.validate_record_operational_state(record)
        
        serializer = HRRecordDetailResponseSerializer(record)
        return ApiResponse.success(data=serializer.data, message="Detailed timesheet graph traced successfully.")


class HRRecordFinalizeAPIView(BaseCompanyAPIView):
    """
    Locks an open daily attendance record sheet to freeze parameters before a payroll run.
    """
    required_permissions = {
        "POST": "tenant.attendance.manage",
    }

    def post(self, request, record_id, *args, **kwargs):
        company = request.company
        admin_actor = request.membership  # Provided automatically by CompanyContextPermission
        
        serializer = HRStandardActionPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        record = HRAttendanceManagementService.finalize_record(
            company=company,
            admin_actor=admin_actor,
            record_id=record_id,
            reason=serializer.validated_data["reason"]
        )
        return ApiResponse.success(message=f"Timesheet ledger row #{record.id} finalized successfully.")


class HRRecordUnlockAPIView(BaseCompanyAPIView):
    """
    Removes processing locks from a finalized timesheet row to permit administrative revisions.
    """
    required_permissions = {
        "POST": "tenant.attendance.manage",
    }

    def post(self, request, record_id, *args, **kwargs):
        company = request.company
        admin_actor = request.membership
        
        serializer = HRStandardActionPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        record = HRAttendanceManagementService.unlock_record(
            company=company,
            admin_actor=admin_actor,
            record_id=record_id,
            reason=serializer.validated_data["reason"]
        )
        return ApiResponse.success(message=f"Timesheet ledger row #{record.id} opened for revisions.")


class HRRecordReprocessAPIView(BaseCompanyAPIView):
    """
    Forces a retrospective computation step using the core business calculations engine.
    """
    required_permissions = {
        "POST": "tenant.attendance.manage",
    }

    def post(self, request, record_id, *args, **kwargs):
        company = request.company
        
        serializer = HRStandardActionPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        record = HRAttendanceManagementService.reprocess_record_timeline(
            company=company,
            record_id=record_id
        )
        return ApiResponse.success(message=f"Calculations updated for record entry #{record.id}.")


class HRManualCorrectionAPIView(BaseCompanyAPIView):
    """
    Injects missed workflow actions into an active data timeline log stream.
    """
    required_permissions = {
        "POST": "tenant.attendance.manage",
    }

    def post(self, request, *args, **kwargs):
        company = request.company
        admin_actor = request.membership
        
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
        return ApiResponse.success(
            data={"event_id": event.id}, 
            message="Manual correction action committed successfully.", 
            status=status.HTTP_201_CREATED
        )