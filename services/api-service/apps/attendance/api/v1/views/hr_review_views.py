# apps/attendance/api/v1/views/hr_review_views.py
from rest_framework import status
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse
from apps.core.standers_pagination import StandardLimitOffsetPagination, PaginationAdapter

# Architectural domain bindings
from apps.attendance.selectors.hr_review_selector import HRReviewSelector
from apps.attendance.services.hr_review_service import HRReviewService
from apps.attendance.services.hr_record_detail_service import HRRecordDetailService
from apps.attendance.api.v1.serializers.hr_record_detail_serializers import ComprehensiveAttendanceRecordDetailSerializer
from apps.attendance.api.v1.serializers.hr_review_serializers import (
    HRReviewDashboardMetricsSerializer,
    HRReviewQueueRowSerializer,
    HRReviewResolveInputSerializer,
    HRReviewNoteInputSerializer
)

class HRReviewDashboardAPIView(BaseCompanyAPIView):
    """
    Exposes high-speed compiled telemetry variables summary metrics for the queue header display.
    """
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, *args, **kwargs):
        metrics_graph = HRReviewSelector.get_dashboard_metrics(company=request.company)
        serializer = HRReviewDashboardMetricsSerializer(metrics_graph)
        return ApiResponse.success(data=serializer.data, message="Review queue overview indicators synchronized.")

class HRReviewQueueListAPIView(BaseCompanyAPIView):
    """
    Serves a paginated subset of processing exceptions for the corporate administration overview grid.
    """
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, *args, **kwargs):
        # Extract query payload filter configurations parameters dictionary
        filter_bounds = request.query_params.dict()
        
        queryset_stream = HRReviewSelector.list_review_records(company=request.company, filters=filter_bounds)
        
        paginator = StandardLimitOffsetPagination()
        paginated_records = paginator.paginate_queryset(queryset_stream, request, view=self)
        
        serializer = HRReviewQueueRowSerializer(paginated_records, many=True)
        pagination_meta = PaginationAdapter.get_metadata(paginator, paginated_records)
        
        return ApiResponse.success(
            data={"results": serializer.data, "pagination": pagination_meta}, 
            message="Review exception logs queue loaded successfully."
        )

class HRReviewItemDetailAPIView(BaseCompanyAPIView):
    """
    Deep-links into the primary historical timesheet record investigation graph packet.
    """
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, record_id, *args, **kwargs):
        # Enforce strict cross-tenant isolation by passing request.company straight down
        packet = HRRecordDetailService.compile_detailed_record_packet(
            company=request.company, 
            record_id=int(record_id)
        )
        if not packet:
            return ApiResponse.error(message="Target investigative record row was not found.", status=status.HTTP_404_NOT_FOUND)
            
        serializer = ComprehensiveAttendanceRecordDetailSerializer(packet)
        return ApiResponse.success(data=serializer.data, message="Investigative timeline record packet loaded.")

class HRReviewResolveAPIView(BaseCompanyAPIView):
    """
    Acknowledge verification and clear active exception flags for the daily ledger statement record.
    """
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request, record_id, *args, **kwargs):
        serializer = HRReviewResolveInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        resolved_record = HRReviewService.resolve_review(
            company=request.company,
            actor=request.membership,
            record_id=int(record_id),
            justification=serializer.validated_data["reason"]
        )
        
        response_data = HRReviewQueueRowSerializer(resolved_record).data
        return ApiResponse.success(
            data=response_data, 
            message="Timesheet calculation anomaly resolved and verified successfully."
        )

class HRReviewNoteAPIView(BaseCompanyAPIView):
    """
    Appends an evaluation comment node straight onto the unalterable audit ledger trace stream.
    """
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request, record_id, *args, **kwargs):
        serializer = HRReviewNoteInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        updated_record = HRReviewService.append_note(
            company=request.company,
            actor=request.membership,
            record_id=int(record_id),
            note_text=serializer.validated_data["reason"]
        )
        
        response_data = HRReviewQueueRowSerializer(updated_record).data
        return ApiResponse.success(
            data=response_data, 
            message="Investigation discussion narrative log written onto tracking node."
        )