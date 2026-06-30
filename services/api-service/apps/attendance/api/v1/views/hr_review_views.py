# apps/attendance/api/v1/views/hr_review_views.py
from rest_framework import status
from django.utils.dateparse import parse_date

# Core architectural boundaries
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse
from apps.core.standers_pagination import (
    StandardLimitOffsetPagination, 
    PaginationAdapter
)          

# Selector and service bindings
from apps.attendance.selectors.hr_review_selector import HRAttendanceReviewSelector
from apps.attendance.services.hr_review_workflow_service import HRReviewWorkflowService
from apps.attendance.api.v1.serializers.hr_review_serializers import (
    HRReviewQueueDashboardSerializer, HRReviewQueueRowSerializer, 
    HRReviewActionInputSerializer, HRReviewAssignmentInputSerializer
)
from apps.attendance.services.hr_record_detail_service import HRRecordDetailService
from apps.attendance.api.v1.serializers.hr_record_detail_serializers import ComprehensiveAttendanceRecordDetailSerializer

class HRReviewDashboardAPIView(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, *args, **kwargs):
        metrics = HRAttendanceReviewSelector.get_queue_dashboard_metrics(company=request.company)
        serializer = HRReviewQueueDashboardSerializer(metrics)
        return ApiResponse.success(data=serializer.data, message="Queue metadata indicators loaded successfully.")

class HRReviewQueueListAPIView(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, *args, **kwargs):
        # 1. Fetch our highly optimized query graph template
        raw_queryset = HRAttendanceReviewSelector.get_review_queue_queryset(company=request.company)

        # 2. Apply parameters filter criteria safely from the request payload
        if request.query_params.get("anomaly_type"):
            raw_queryset = raw_queryset.filter(computed_anomaly_type=request.query_params.get("anomaly_type"))
        if request.query_params.get("priority"):
            raw_queryset = raw_queryset.filter(computed_priority=request.query_params.get("priority"))

        # 3. Apply standard limit-offset pagination configurations server-side
        paginator = StandardLimitOffsetPagination()
        paginated_qs = paginator.paginate_queryset(raw_queryset, request, view=self)
        
        serializer = HRReviewQueueRowSerializer(paginated_qs, many=True)
        pagination_meta = PaginationAdapter.get_metadata(paginator, paginated_qs)

        return ApiResponse.success(data={"results": serializer.data, "pagination": pagination_meta}, message="Review queue feed loaded.")

class HRReviewItemDetailAPIView(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, pk, *args, **kwargs):
        """
        Reuses the comprehensive detail packet definition contract from Phase 4.
        """
        packet = HRRecordDetailService.compile_detailed_record_packet(company=request.company, record_id=int(pk))
        if not packet:
            return ApiResponse.error(message="Target exception record not found.", status=status.HTTP_404_NOT_FOUND)
            
        serializer = ComprehensiveAttendanceRecordDetailSerializer(packet)
        return ApiResponse.success(data=serializer.data, message="Review row metrics graph loaded.")

class HRReviewAssignAPIView(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request, pk, *args, **kwargs):
        serializer = HRReviewAssignmentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        HRReviewWorkflowService.assign_reviewer_to_item(
            company=request.company, actor=request.membership, record_id=int(pk),
            reviewer_id=serializer.validated_data["reviewer_id"], note=serializer.validated_data["reason"]
        )
        return ApiResponse.success(message="Reviewer profile mapped successfully onto exception target.")

class HRReviewResolveAPIView(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request, pk, *args, **kwargs):
        serializer = HRReviewActionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Pull the incoming action parameter mapping string directly out of the route request elements
        action_route = self.request.path.split("/")[-2].upper()  # Mapped token profiles: RESOLVE, REJECT, ESCALATE
        
        HRReviewWorkflowService.resolve_exception_item(
            company=request.company, actor=request.membership, record_id=int(pk),
            resolution_status=action_route, note=serializer.validated_data["reason"]
        )
        return ApiResponse.success(message=f"Exception status action token tracking change applied: {action_route}")

class HRReviewNoteAPIView(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request, pk, *args, **kwargs):
        serializer = HRReviewActionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        HRReviewWorkflowService.append_internal_review_note(
            company=request.company, actor=request.membership, record_id=int(pk),
            note_text=serializer.validated_data["reason"]
        )
        return ApiResponse.success(message="Discussion statement appended successfully onto evaluation trail.")