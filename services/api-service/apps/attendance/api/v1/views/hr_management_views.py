# apps/attendance/api/v1/views/hr_management_views.py
from datetime import datetime

from apps.attendance.selectors.hr_dashboard_selector import HRDashboardSelector
from rest_framework import status
from django.utils import timezone
from django.utils.dateparse import parse_date
import zoneinfo
from apps.companies.models import Company
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse

from apps.attendance.selectors.hr_management_selector import HRAttendanceManagementSelector
from apps.attendance.services.hr_management_service import HRAttendanceManagementService
from apps.attendance.validators.hr_foundation_validator import HRFoundationValidator
from apps.attendance.api.v1.serializers.hr_serializers import (
    HRDailyLedgerOutputSerializer,
    HRRecordDetailResponseSerializer,
    HRManualPunchInjectionSerializer,
    HRStandardActionPayloadSerializer
)
from apps.attendance.api.v1.serializers.hr_dashboard_serializers import MasterDashboardResponseGraphSerializer

class HRDashboardSummaryAPIView(BaseCompanyAPIView):
    """
    Real-time multi-tenant operational control center view controller layer.
    Compiles data metrics on demand using lightweight database-level annotations.
    """
    required_permissions = {
        "GET": "tenant.attendance.view",
    }

    def get(self, request, *args, **kwargs):
        company = request.company
        
        # 1. Parse date parameters, falling back to the target company's current timezone context
        date_param = request.query_params.get("date")
        company_tz_str = getattr(company, "timezone", "UTC")
        
        try:
            local_zone = zoneinfo.ZoneInfo(company_tz_str)
        except Exception:
            local_zone = zoneinfo.ZoneInfo("UTC")

        now_local = timezone.now().astimezone(local_zone)
        target_date = parse_date(date_param) if date_param else now_local.date()
        
        if not target_date:
            return ApiResponse.error(
                message="Validation Error: Invalid format provided for date parameter.", 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Extract operational time configurations
        current_time_local = now_local.time() if target_date == now_local.date() else datetime.time(23, 59, 59)

        # 3. Assemble components using our read-only selectors
        summary_cards = HRDashboardSelector.get_dashboard_summary(
            company=company, target_date=target_date, current_time_local=current_time_local
        )
        departments_list = HRDashboardSelector.get_department_summary(
            company=company, target_date=target_date, current_time_local=current_time_local
        )
        shifts_list = HRDashboardSelector.get_shift_summary(
            company=company, target_date=target_date, current_time_local=current_time_local
        )
        live_workforce_list = HRDashboardSelector.get_live_workforce(
            company=company, target_date=target_date, current_time_local=current_time_local
        )
        activity_feed_qs = HRDashboardSelector.get_activity_feed(
            company=company, target_date=target_date
        )

        # 4. Construct metadata payload definitions
        metadata = {
            "summary_date": target_date,
            "generated_at": timezone.now(),
            "timezone": company_tz_str,
            "company_name": company.name
        }

        # 5. Serialize data structures into a single response object
        master_payload = {
            "summary": summary_cards,
            "departments": departments_list,
            "shift_distribution": shifts_list,
            "live_workforce": live_workforce_list,
            "activity_feed": activity_feed_qs,
            "metadata": metadata
        }

        serializer = MasterDashboardResponseGraphSerializer(master_payload)
        return ApiResponse.success(
            data=serializer.data, 
            message="Granular real-time corporate attendance dashboard summary compiled successfully."
        )
    

    

class HRCompanyLedgerAPIView(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request, *args, **kwargs):
        # Parse query parameters safely
        date_from = parse_date(request.query_params.get("date_from", ""))
        date_to = parse_date(request.query_params.get("date_to", ""))
        status_filter = request.query_params.get("status")
        dept_id = request.query_params.get("department_id")
        search_query = request.query_params.get("search")
        
        review_req = request.query_params.get("review_required")
        review_bool = review_req.lower() == "true" if review_req else None
        
        ledger_qs = HRAttendanceManagementSelector.list_daily_attendance_ledger(
            company=request.company,
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
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request, record_id, *args, **kwargs):
        record = HRAttendanceManagementSelector.get_base_hr_queryset(company=request.company).filter(id=record_id).first()
        HRFoundationValidator.validate_record_operational_state(record)
        
        serializer = HRRecordDetailResponseSerializer(record)
        return ApiResponse.success(data=serializer.data, message="Detailed timesheet graph loaded.")


class HRRecordFinalizeAPIView(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request, record_id, *args, **kwargs):
        serializer = HRStandardActionPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        record = HRAttendanceManagementService.finalize_record(
            company=request.company,
            admin_actor=request.membership,
            record_id=int(record_id),
            reason=serializer.validated_data["reason"]
        )
        return ApiResponse.success(message=f"Timesheet record row #{record.id} finalized successfully.")


class HRRecordUnlockAPIView(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request, record_id, *args, **kwargs):
        serializer = HRStandardActionPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        record = HRAttendanceManagementService.unlock_record(
            company=request.company,
            admin_actor=request.membership,
            record_id=int(record_id),
            reason=serializer.validated_data["reason"]
        )
        return ApiResponse.success(message=f"Timesheet record row #{record.id} unlocked successfully.")


class HRRecordReprocessAPIView(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request, record_id, *args, **kwargs):
        serializer = HRStandardActionPayloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        record = HRAttendanceManagementService.reprocess_record_timeline(
            company=request.company,
            admin_actor=request.membership,
            record_id=int(record_id),
            reason=serializer.validated_data["reason"]
        )
        return ApiResponse.success(message=f"Calculations updated for record entry #{record.id}.")


class HRManualCorrectionAPIView(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request, *args, **kwargs):
        serializer = HRManualPunchInjectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        target_employee = HRFoundationValidator.validate_target_employee(
            serializer.validated_data["membership_id"], request.company
        )
        
        event = HRAttendanceManagementService.inject_manual_correction_event(
            company=request.company,
            admin_actor=request.membership,
            target_member=target_employee,
            data=serializer.validated_data
        )
        return ApiResponse.success(
            data={"event_id": event.id}, 
            message="Manual correction action committed successfully.", 
            status=status.HTTP_201_CREATED
        )