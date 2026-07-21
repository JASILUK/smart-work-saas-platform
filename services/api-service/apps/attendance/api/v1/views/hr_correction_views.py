# apps/attendance/api/v1/views/hr_correction_views.py
"""
HR Administrative Core Event Correction API Processing View
"""

from rest_framework import status
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse

from apps.attendance.api.v1.serializers.hr_correction_serializers import HRAttendanceEventCorrectionSerializer
from apps.attendance.services.hr_correction_service import HRAttendanceCorrectionService
from apps.attendance.services.hr_record_detail_service import HRRecordDetailService
from apps.attendance.api.v1.serializers.hr_record_detail_serializers import ComprehensiveAttendanceRecordDetailSerializer


class HRAttendanceEventCorrectionAPIView(BaseCompanyAPIView):
    """
    Processes updates/inserts to Attendance Events and outputs the synchronized summary graph.
    """
    required_permissions = {
        "POST": "tenant.attendance.manage",
    }

    def post(self, request, *args, **kwargs):
        # 1. Deserialize request parameters
        serializer = HRAttendanceEventCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data

        # 2. Extract operator membership context using request context variables
        operator_membership = getattr(request, "membership", None)
        if not operator_membership:
            return ApiResponse.error(
                message="Administrative actor context verification failed within this transaction context.",
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 3. Delegate execution flow parameters cleanly down to core transaction handlers
        HRAttendanceCorrectionService.process_event_correction(
            company=request.company,
            operator=operator_membership,
            membership_id=params["membership_id"],
            target_date=params["target_date"],
            event_id=params.get("event_id"),
            event_type=params.get("event_type"),
            event_time=params["event_time"],
            notes=params["notes"]
        )

        # 4. Extract target summary logs from the structural graph data layers to build an updated response envelope
        refreshed_packet = HRRecordDetailService.compile_detailed_record_packet_by_date(
            company=request.company,
            membership_id=params["membership_id"],
            target_date=params["target_date"]
        )

        # 5. Return updated values using the standard system serializer contracts
        response_serializer = ComprehensiveAttendanceRecordDetailSerializer(refreshed_packet)
        return ApiResponse.success(
            data=response_serializer.data,
            message="Attendance event correction committed successfully. Timesheet analytics recalculated automatically.",
            status=status.HTTP_200_OK
        )