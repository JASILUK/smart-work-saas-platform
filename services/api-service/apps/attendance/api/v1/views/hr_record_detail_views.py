# apps/attendance/api/v1/views/hr_record_detail_views.py
from rest_framework import status
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse 
from apps.attendance.services.hr_record_detail_service import HRRecordDetailService
from apps.attendance.api.v1.serializers.hr_record_detail_serializers import ComprehensiveAttendanceRecordDetailSerializer

class HRAttendanceRecordDetailAPIView(BaseCompanyAPIView):
    """
    Enterprise-grade endpoint exposing an individual DailyAttendance timesheet snapshot record.
    Authentication, workspace checks, subscription validation, and RBAC permission string guards
    are managed automatically by the permission classes of the base class.
    """
    
    # Restrict endpoint usage to authorized actors via RolePermission mapping rules
    required_permissions = {
        "GET": "tenant.attendance.manage",
    }

    def get(self, request, record_id, *args, **kwargs):
        # 1. Compile the comprehensive data packet using our orchestrator service
        packet = HRRecordDetailService.compile_detailed_record_packet(
            company=request.company,
            record_id=int(record_id)
        )

        # 2. Return a clean 404 error if the record does not exist within the active tenant context
        if not packet:
            return ApiResponse.error(
                message=f"Attendance record identifier #{record_id} does not exist within this workspace context.",
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. Serialize structural modules using optimized read pathways
        serializer = ComprehensiveAttendanceRecordDetailSerializer(packet)

        # 4. Deliver response payload cleanly using standard envelope formatting
        return ApiResponse.success(
            data=serializer.data,
            message="Detailed chronological timesheet audit graph compiled successfully.",
            status=status.HTTP_200_OK
        )