# apps/attendance/api/v1/views/hr_report_views.py
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse
from rest_framework import status
from apps.attendance.selectors.hr_report_selectors import HRReportDataSelector
from apps.attendance.services.hr_report_service import HRReportOrchestratorService
from apps.attendance.models.report_models import HRReportGenerationHistory, HRReportAutomationSchedule
from apps.attendance.api.v1.serializers.hr_report_serializers import (
    HRReportSummaryMetricsSerializer, HRPayrollSummaryRowSerializer,
    HRReportExportTriggerInputSerializer, HRReportScheduleInputSerializer,
    HRReportGenerationHistorySerializer
)

class HRCompanyReportSummaryAPIView(BaseCompanyAPIView):
    """
    Exposes aggregated period statistics and corporate KPIs over defined date windows.
    """
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, *args, **kwargs):
        clean_filters = HRReportOrchestratorService.parse_and_validate_filters(request.query_params.dict())
        metrics_dict = HRReportDataSelector.get_historical_summary_metrics(company=request.company, filters=clean_filters)
        
        serializer = HRReportSummaryMetricsSerializer(metrics_dict)
        return ApiResponse.success(data=serializer.data, message="Historical summary metrics compiled.")

class HRPayrollAttendanceDatasetAPIView(BaseCompanyAPIView):
    """
    Returns high-speed timesheet summaries for payroll preparation.
    """
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, *args, **kwargs):
        clean_filters = HRReportOrchestratorService.parse_and_validate_filters(request.query_params.dict())
        payroll_qs = HRReportDataSelector.get_payroll_dataset(company=request.company, filters=clean_filters)
        
        serializer = HRPayrollSummaryRowSerializer(payroll_qs, many=True)
        return ApiResponse.success(data={"results": serializer.data}, message="Payroll dataset ledger extracted.")

class HRReportAnalyticsAPIView(BaseCompanyAPIView):
    """
    Returns chart-ready metrics and data vectors for executive dashboard widgets.
    """
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, *args, **kwargs):
        clean_filters = HRReportOrchestratorService.parse_and_validate_filters(request.query_params.dict())
        analytics_bundle = HRReportDataSelector.get_analytics_trends(company=request.company, filters=clean_filters)
        return ApiResponse.success(data=analytics_bundle, message="Analytical distribution metrics loaded.")

class HRReportExportTriggerAPIView(BaseCompanyAPIView):
    """
    Queues a high-performance reporting task in the background and returns a generation tracking token.
    """
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request, *args, **kwargs):
        serializer = HRReportExportTriggerInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        task_entry = HRReportOrchestratorService.trigger_async_report_export(
            company=request.company, actor=request.membership, data=serializer.validated_data
        )
        
        # Simulate immediate background compilation task execution for validation purposes
        # In live production environments, remove this line to allow separate task workers to pick up the item.
        HRReportOrchestratorService.execute_streaming_csv_generation(task_entry.id)
        
        task_entry.refresh_from_db()
        return ApiResponse.success(
            data={"task_id": task_entry.id, "status": task_entry.status, "download_url": task_entry.file_url},
            message="Asynchronous export document task successfully initialized."
        )

class HRReportAutomationSchedulingAPIView(BaseCompanyAPIView):
    """
    Allows administrators to configure and store recurring report automation rules.
    """
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request, *args, **kwargs):
        serializer = HRReportScheduleInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        schedule = HRReportOrchestratorService.save_automated_report_schedule(
            company=request.company, actor=request.membership, data=serializer.validated_data
        )
        return ApiResponse.success(data={"schedule_id": schedule.id}, message="Automated reporting schedule entry registered.")

class HRReportGenerationHistoryAPIView(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.manage"}

    def get(self, request, *args, **kwargs):
        history_qs = HRReportGenerationHistory.objects.filter(company=request.company)
        serializer = HRReportGenerationHistorySerializer(history_qs, many=True)
        return ApiResponse.success(data={"results": serializer.data}, message="Report audit trail logged entries loaded.")