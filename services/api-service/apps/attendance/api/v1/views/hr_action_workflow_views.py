# apps/attendance/api/v1/views/hr_action_workflow_views.py
from rest_framework import status
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse

# Engine and business layout dependencies
from apps.attendance.services.hr_action_workflow_service import HRAttendanceActionWorkflowService
from apps.attendance.api.v1.serializers.hr_action_serializers import (
    HRBaseActionInputSerializer, HRManualPunchInputSerializer, HROverrideStatusInputSerializer
)
from apps.attendance.api.v1.serializers.hr_record_detail_serializers import ComprehensiveAttendanceRecordDetailSerializer
from apps.attendance.selectors.hr_record_detail_selector import HRRecordDetailSelector
from apps.attendance.services.hr_record_detail_service import HRRecordDetailService

class HRBaseActionWorkflowAPIView(BaseCompanyAPIView):
    """
    Abstract blueprint anchoring structural administrative action controller views.
    """
    required_permissions = {
        "POST": "tenant.attendance.manage",
    }

    def _render_updated_graph_response(self, request, record_id: int, success_message: str) -> ApiResponse:
        """
        Helper that builds and returns the comprehensive record graph payload 
        following a successful structural state change mutation.
        """
        packet = HRRecordDetailService.compile_detailed_record_packet(company=request.company, record_id=record_id)
        serializer = ComprehensiveAttendanceRecordDetailSerializer(packet)
        return ApiResponse.success(data=serializer.data, message=success_message, status=status.HTTP_200_OK)

class HRManualCheckInAPIView(HRBaseActionWorkflowAPIView):
    def post(self, request, record_id, *args, **kwargs):
        serializer = HRManualPunchInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        HRAttendanceActionWorkflowService.execute_manual_check_in(
            company=request.company, actor=request.membership, record_id=int(record_id), data=serializer.validated_data
        )
        return self._render_updated_graph_response(request, int(record_id), "Administrative Check-In event registered successfully.")

class HRManualCheckOutAPIView(HRBaseActionWorkflowAPIView):
    def post(self, request, record_id, *args, **kwargs):
        serializer = HRManualPunchInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        HRAttendanceActionWorkflowService.execute_manual_check_out(
            company=request.company, actor=request.membership, record_id=int(record_id), data=serializer.validated_data
        )
        return self._render_updated_graph_response(request, int(record_id), "Administrative Check-Out event registered successfully.")

class HRManualBreakStartAPIView(HRBaseActionWorkflowAPIView):
    def post(self, request, record_id, *args, **kwargs):
        serializer = HRManualPunchInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        HRAttendanceActionWorkflowService.execute_manual_break_action(
            company=request.company, actor=request.membership, record_id=int(record_id), action_type="BREAK_OUT", data=serializer.validated_data
        )
        return self._render_updated_graph_response(request, int(record_id), "Break duration window initialized successfully.")

class HRManualBreakEndAPIView(HRBaseActionWorkflowAPIView):
    def post(self, request, record_id, *args, **kwargs):
        serializer = HRManualPunchInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        HRAttendanceActionWorkflowService.execute_manual_break_action(
            company=request.company, actor=request.membership, record_id=int(record_id), action_type="BREAK_IN", data=serializer.validated_data
        )
        return self._render_updated_graph_response(request, int(record_id), "Break intermission window terminated successfully.")

class HROverrideStatusAPIView(HRBaseActionWorkflowAPIView):
    def post(self, request, record_id, *args, **kwargs):
        serializer = HROverrideStatusInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        HRAttendanceActionWorkflowService.execute_status_override(
            company=request.company, actor=request.membership, record_id=int(record_id), data=serializer.validated_data
        )
        return self._render_updated_graph_response(request, int(record_id), "Synthesis calculation status overridden successfully.")

class HRFinalizeRecordAPIView(HRBaseActionWorkflowAPIView):
    def post(self, request, record_id, *args, **kwargs):
        serializer = HRBaseActionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        HRAttendanceActionWorkflowService.execute_finalize(
            company=request.company, actor=request.membership, record_id=int(record_id), data=serializer.validated_data
        )
        return self._render_updated_graph_response(request, int(record_id), "Attendance record locked for payroll finalization.")

class HRUnlockRecordAPIView(HRBaseActionWorkflowAPIView):
    def post(self, request, record_id, *args, **kwargs):
        serializer = HRBaseActionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        HRAttendanceActionWorkflowService.execute_unlock(
            company=request.company, actor=request.membership, record_id=int(record_id), data=serializer.validated_data
        )
        return self._render_updated_graph_response(request, int(record_id), "Payroll processing lock cleared from target record.")

class HRReprocessTimelineAPIView(HRBaseActionWorkflowAPIView):
    def post(self, request, record_id, *args, **kwargs):
        serializer = HRBaseActionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        HRAttendanceActionWorkflowService.execute_reprocess_or_recalculate(
            company=request.company, actor=request.membership, record_id=int(record_id), data=serializer.validated_data
        )
        return self._render_updated_graph_response(request, int(record_id), "Timeline metric evaluation synchronized successfully.")

class HRMarkNeedsReviewAPIView(HRBaseActionWorkflowAPIView):
    def post(self, request, record_id, *args, **kwargs):
        serializer = HRBaseActionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        HRAttendanceActionWorkflowService.execute_review_toggle(
            company=request.company, actor=request.membership, record_id=int(record_id), set_flag=True, data=serializer.validated_data
        )
        return self._render_updated_graph_response(request, int(record_id), "Attention exception alert flag raised successfully.")

class HRClearReviewAPIView(HRBaseActionWorkflowAPIView):
    def post(self, request, record_id, *args, **kwargs):
        serializer = HRBaseActionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        HRAttendanceActionWorkflowService.execute_review_toggle(
            company=request.company, actor=request.membership, record_id=int(record_id), set_flag=False, data=serializer.validated_data
        )
        return self._render_updated_graph_response(request, int(record_id), "Attention exception alert flag cleared successfully.")