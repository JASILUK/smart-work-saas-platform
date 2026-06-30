from django.urls import path

# ─── 1. Core Work Schedule Management Views
from apps.attendance.api.v1.views.attendance_access_views import (
    AttendanceAccessResolutionAPI, AttendanceAccessRuleDetailAPI, 
    AttendanceAccessRuleListCreateAPI, CompanyAttendanceDefaultAPI, 
    EmployeeAttendanceOverrideDetailAPI, EmployeeAttendanceOverrideListCreateAPI
)
from apps.attendance.api.v1.views.attendance_event_views import (
    AttendanceBreakInAPI, AttendanceBreakOutAPI, AttendanceCheckInAPI, 
    AttendanceCheckOutAPI, AttendanceEventDetailAPI, AttendanceEventListAPI, 
    LiveAttendanceSummaryAPI, ManualAttendanceAPI
)
from apps.attendance.api.v1.views.attendance_location_views import (
    ActivateAttendanceLocationAPI, AttendanceLocationDetailAPI, AttendanceLocationListCreateAPI
)
from apps.attendance.api.v1.views.biometric_log_views import (
    BiometricLogDetailAPI, BiometricLogListAPI, ManualImportAPI, PushWebhookAPI
)
from apps.attendance.api.v1.views.biometric_views import (
    BiometricDeviceActivateAPI, BiometricDeviceDetailAPI, BiometricDeviceListCreateAPI, 
    BiometricEmployeeMappingActivateAPI, BiometricEmployeeMappingDetailAPI, 
    BiometricEmployeeMappingListCreateAPI
)
from apps.attendance.api.v1.views.company_attendance_method_views import (
    CompanyAttendanceMethodAPI, CompanyAttendanceMethodActionAPI
)
from apps.attendance.api.v1.views.company_work_schedule_api import (
    CompanyWorkScheduleAPI, CompanyWorkScheduleDetailAPI, CompanyWorkScheduleActivationAPI
)

# ─── 2. Core Holiday CRUD & Listing Views
from apps.attendance.api.v1.views.daily_attendance_views import (
    DailyAttendanceDetailAPI, DailyAttendanceFinalizeAPI, DailyAttendanceListAPI, 
    DailyAttendanceReprocessAPI, DailyAttendanceReviewsAPI
)
from apps.attendance.api.v1.views.employee_dashboard_view import EmployeeDashboardAPIView
from apps.attendance.api.v1.views.face_enrollment_views import (
    CompanyFaceEnrollmentPolicyAPI, EmployeeSelfEnrollmentAPI, FaceEnrollmentApproveAPI, 
    FaceEnrollmentDetailAPI, FaceEnrollmentListAPI, FaceEnrollmentRejectAPI, 
    FaceEnrollmentRevokeAPI, HRInstructionEnrollmentAPI
)
from apps.attendance.api.v1.views.holiday_views import (
    HolidayListCreateAPI, HolidayDetailAPI, HolidayImportAPI, HolidayPreviewAPI
)

# ─── 3. Employee History Module Views
from apps.attendance.api.v1.views.hr_action_workflow_views import HRClearReviewAPIView, HRFinalizeRecordAPIView, HRManualBreakEndAPIView, HRManualBreakStartAPIView, HRManualCheckInAPIView, HRManualCheckOutAPIView, HRMarkNeedsReviewAPIView, HROverrideStatusAPIView, HRReprocessTimelineAPIView, HRUnlockRecordAPIView
from apps.attendance.api.v1.views.hr_directory_views import HREmployeeAttendanceDirectoryAPIView
from apps.attendance.api.v1.views.hr_profile_views import HREmployeeAttendanceProfileAPIView
from apps.attendance.api.v1.views.hr_record_detail_views import HRAttendanceRecordDetailAPIView
from apps.attendance.api.v1.views.my_attendance_views import (
    MyAttendanceRecordsAPI, MyAttendanceSummaryAPI, MyAttendanceCalendarAPI, 
    MyAttendanceDetailAPI, MyAttendanceTrendsView
)
from apps.attendance.api.v1.views.attendance_management_views import (
    AttendanceManagementListAPI, AttendanceManagementDetailAPI, AttendanceManagementAnalyticsAPI
)

# ─── 4. Reusable Core Shift Configurations Views
from apps.attendance.api.v1.views.shift_views import (
    ShiftListCreateAPI, ShiftDetailAPI, ActivateShiftAPI, SetDefaultShiftAPI
)
from apps.attendance.api.v1.views.employee_shift_assignemnt_view import (
    EmployeeShiftAssignmentListCreateAPI, EmployeeShiftAssignmentDetailAPI, 
    EndEmployeeShiftAssignmentAPI, DeactivateEmployeeShiftAssignmentAPI, 
    BulkAssignEmployeeShiftAPI, TransferEmployeeShiftAPI
)

# ─── 5. Attendance Policy Administration Views
from apps.attendance.api.v1.views.attendance_policy_views import (
    AttendancePolicyDetailAPI, AttendancePolicyUpdateAPI, AttendancePolicyResetAPI
)
from apps.attendance.api.v1.views.verification_views import FaceVerifyAPIView, GPSVerifyAPIView

# ─── 6. Leave Balances & Applications Management Views
from apps.attendance.api.v1.views.leave_views import (
    MyLeaveBalancesAPI, MyLeaveRequestsAPI, MyLeaveRequestDetailAPI, MyLeaveRequestCancelAPI, 
    LeaveRequestListAPI, LeaveRequestDetailAPI, LeaveRequestApproveAPI, LeaveRequestRejectAPI, 
    LeaveRequestCancelHRAPI, EmployeeLeaveBalancesAPI, EmployeeLeaveRequestsAPI, 
    LeaveTypeListCreateAPI, LeaveTypeDetailUpdateDeleteAPI, LeaveBalanceListAPI, 
    LeaveBalanceAdjustAPI, LeaveBalanceAllocateAPI
)

# ─── 7. HR Attendance Management Core Extensions (New Operations Dashboard)
from apps.attendance.api.v1.views.hr_management_views import (
    HRManualCorrectionAPIView, HRCompanyLedgerAPIView, 
    HRDashboardSummaryAPIView, 
)

from apps.attendance.api.v1.views.hr_review_views import (
    HRReviewDashboardAPIView, HRReviewQueueListAPIView, HRReviewItemDetailAPIView,
    HRReviewAssignAPIView, HRReviewResolveAPIView, HRReviewNoteAPIView
)

from apps.attendance.api.v1.views.hr_report_views import (
    HRCompanyReportSummaryAPIView, HRPayrollAttendanceDatasetAPIView, 
    HRReportAnalyticsAPIView, HRReportExportTriggerAPIView, 
    HRReportAutomationSchedulingAPIView, HRReportGenerationHistoryAPIView
)


app_name = "attendance"

urlpatterns = [
    # =====================================================
    # COMPANY WORK SCHEDULE RULES
    # =====================================================
    path("schedule/", CompanyWorkScheduleAPI.as_view(), name="company-schedule"),
    path("schedule/detail/", CompanyWorkScheduleDetailAPI.as_view(), name="company-schedule-detail"),
    path("schedule/activation/", CompanyWorkScheduleActivationAPI.as_view(), name="company-schedule-activation"),

    # =====================================================
    # HOLIDAY COMPLIANCE CRUD
    # =====================================================
    path("holidays/", HolidayListCreateAPI.as_view(), name="holiday-list-create"),
    path("holidays/<int:holiday_id>/", HolidayDetailAPI.as_view(), name="holiday-detail"),

    # =====================================================
    # EXTERNAL COMPLIANCE IMPORT PIPELINES
    # =====================================================
    path("holidays/import/", HolidayImportAPI.as_view(), name="holiday-import"),
    path("holidays/import/preview/", HolidayPreviewAPI.as_view(), name="holiday-import-preview"),

    # =====================================================
    # REUSABLE SHIFT CONFIGURATIONS
    # =====================================================
    path("shifts/", ShiftListCreateAPI.as_view(), name="shift-list-create"),
    path("shifts/<int:public_id>/", ShiftDetailAPI.as_view(), name="shift-detail"),
    path("shifts/<int:public_id>/activate/", ActivateShiftAPI.as_view(), name="shift-activate"),
    path("shifts/<int:public_id>/set-default/", SetDefaultShiftAPI.as_view(), name="shift-set-default"),

    # =====================================================
    # EMPLOYEE SHIFT ASSIGNMENTS
    # =====================================================
    path("assignments/", EmployeeShiftAssignmentListCreateAPI.as_view(), name="assignment-list-create"),
    path("assignments/<int:pk>/", EmployeeShiftAssignmentDetailAPI.as_view(), name="assignment-detail"),
    path("assignments/<int:pk>/end/", EndEmployeeShiftAssignmentAPI.as_view(), name="assignment-end"),
    path("assignments/<int:pk>/deactivate/", DeactivateEmployeeShiftAssignmentAPI.as_view(), name="assignment-deactivate"),
    path("assignments/<int:pk>/transfer/", TransferEmployeeShiftAPI.as_view(), name="assignment-transfer"),
    path("assignments/bulk-assign/", BulkAssignEmployeeShiftAPI.as_view(), name="assignment-bulk-assign"),

    # =====================================================
    # ATTENDANCE INTERPRETATION POLICIES
    # =====================================================
    path("policy/", AttendancePolicyDetailAPI.as_view(), name="attendance-policy-detail"),
    path("policy/update/", AttendancePolicyUpdateAPI.as_view(), name="attendance-policy-update"),
    path("policy/reset/", AttendancePolicyResetAPI.as_view(), name="attendance-policy-reset"),
    path("methods/", CompanyAttendanceMethodAPI.as_view(), name="company-attendance-methods-overview"),
    path("methods/<str:method_name>/", CompanyAttendanceMethodActionAPI.as_view(), name="company-attendance-method-soft-delete"),
    path("methods/<str:method_name>/enable/", CompanyAttendanceMethodActionAPI.as_view(), name="company-attendance-method-enable"),

    path("locations/", AttendanceLocationListCreateAPI.as_view(), name="attendance-locations-list-create"),
    path("locations/<int:location_id>/", AttendanceLocationDetailAPI.as_view(), name="attendance-location-detail"),
    path("locations/<int:location_id>/activate/", ActivateAttendanceLocationAPI.as_view(), name="attendance-location-activate"),

    path("access/defaults/", CompanyAttendanceDefaultAPI.as_view(), name="attendance-access-defaults"),
    path("access/rules/", AttendanceAccessRuleListCreateAPI.as_view(), name="attendance-access-rules-list-create"),
    path("access/rules/<int:rule_id>/", AttendanceAccessRuleDetailAPI.as_view(), name="attendance-access-rule-detail"),
    path("access/overrides/", EmployeeAttendanceOverrideListCreateAPI.as_view(), name="attendance-access-overrides-list-create"),
    path("access/rules/overrides/<int:override_id>/", EmployeeAttendanceOverrideDetailAPI.as_view(), name="attendance-access-override-detail"),
    path("access/resolve/", AttendanceAccessResolutionAPI.as_view(), name="attendance-access-resolve-profile"),

    path("face-enrollments/policy/", CompanyFaceEnrollmentPolicyAPI.as_view(), name="face-policy-management"),
    path("face-enrollments/self/", EmployeeSelfEnrollmentAPI.as_view(), name="face-self-enrollment"),
    path("face-enrollments/hr/", HRInstructionEnrollmentAPI.as_view(), name="face-hr-enrollment"),
    path("face-enrollments/", FaceEnrollmentListAPI.as_view(), name="face-enrollments-list"),
    path("face-enrollments/<int:pk>/", FaceEnrollmentDetailAPI.as_view(), name="face-enrollment-detail"),
    path("face-enrollments/<int:pk>/approve/", FaceEnrollmentApproveAPI.as_view(), name="face-enrollment-approve"),
    path("face-enrollments/<int:pk>/reject/", FaceEnrollmentRejectAPI.as_view(), name="face-enrollment-reject"),
    path("face-enrollments/<int:pk>/revoke/", FaceEnrollmentRevokeAPI.as_view(), name="face-enrollment-revoke"),

    path("biometric/devices/", BiometricDeviceListCreateAPI.as_view(), name="biometric-devices-list-create"),
    path("biometric/devices/<int:pk>/", BiometricDeviceDetailAPI.as_view(), name="biometric-device-detail"),
    path("biometric/devices/<int:pk>/activate/", BiometricDeviceActivateAPI.as_view(), name="biometric-device-activate"),
    path("biometric/mappings/", BiometricEmployeeMappingListCreateAPI.as_view(), name="biometric-mappings-list-create"),
    path("biometric/mappings/<int:pk>/", BiometricEmployeeMappingDetailAPI.as_view(), name="biometric-mapping-detail"),
    path("biometric/mappings/<int:pk>/activate/", BiometricEmployeeMappingActivateAPI.as_view(), name="biometric-mapping-activate"),
    path("biometric/logs/", BiometricLogListAPI.as_view(), name="biometric-logs-list"),
    path("biometric/logs/<int:pk>/", BiometricLogDetailAPI.as_view(), name="biometric-log-detail"),
    path("biometric/logs/import/", ManualImportAPI.as_view(), name="biometric-manual-import"),
    path("biometric/webhooks/push/", PushWebhookAPI.as_view(), name="biometric-device-push-webhook"),

    path("verify/gps/", GPSVerifyAPIView.as_view(), name="verify-gps"),
    path("verify/face/", FaceVerifyAPIView.as_view(), name="verify-face"),
    
    path("punch/check-in/", AttendanceCheckInAPI.as_view(), name="attendance-check-in"),
    path("punch/break-out/", AttendanceBreakOutAPI.as_view(), name="attendance-break-out"),
    path("punch/break-in/", AttendanceBreakInAPI.as_view(), name="attendance-break-in"),
    path("punch/check-out/", AttendanceCheckOutAPI.as_view(), name="attendance-check-out"),
    path("punch/events/", AttendanceEventListAPI.as_view(), name="attendance-events-tracker-list"),
    path("punch/events/<int:pk>/", AttendanceEventDetailAPI.as_view(), name="attendance-event-tracker-detail"),
    path("punch/manual-override/", ManualAttendanceAPI.as_view(), name="attendance-manual-override-adjust"),
    path("punch/live-summary/", LiveAttendanceSummaryAPI.as_view(), name="attendance-live-dashboard-summary"),

    path("daily/", DailyAttendanceListAPI.as_view(), name="daily-attendance-summary-list"),
    path("daily/<int:pk>/", DailyAttendanceDetailAPI.as_view(), name="daily-attendance-summary-detail"),
    path("daily/reprocess/", DailyAttendanceReprocessAPI.as_view(), name="daily-attendance-pipeline-reprocess"),
    path("daily/finalize/", DailyAttendanceFinalizeAPI.as_view(), name="daily-attendance-sheet-finalize"),
    path("daily/reviews/", DailyAttendanceReviewsAPI.as_view(), name="daily-attendance-exceptions-reviews"),

    path("dashboard/", EmployeeDashboardAPIView.as_view(), name="attendance-dashboard"),

    # =====================================================
    # MY ATTENDANCE PORTAL
    # =====================================================
    path("my-attendance/", MyAttendanceRecordsAPI.as_view(), name="my-attendance-list"),
    path("my-attendance/summary/", MyAttendanceSummaryAPI.as_view(), name="my-attendance-summary"),
    path("my-attendance/calendar/", MyAttendanceCalendarAPI.as_view(), name="my-attendance-calendar"),
    path("my-attendance/trends/", MyAttendanceTrendsView.as_view(), name="my-attendance-trends"),
    path("my-attendance/<int:pk>/", MyAttendanceDetailAPI.as_view(), name="my-attendance-detail"),

    # =====================================================
    # OLD WORKFORCE MANAGEMENT LOOKUPS
    # =====================================================
    path("attendance-management/", AttendanceManagementListAPI.as_view(), name="attendance-management-list"),
    path("attendance-management/analytics/", AttendanceManagementAnalyticsAPI.as_view(), name="attendance-management-analytics"),
    path("attendance-management/<int:pk>/", AttendanceManagementDetailAPI.as_view(), name="attendance-management-detail"),

    # =====================================================
    # MY LEAVE REQUESTS
    # =====================================================
    path("me/leave-balances/", MyLeaveBalancesAPI.as_view(), name="my-leave-balances"),
    path("me/leave-requests/", MyLeaveRequestsAPI.as_view(), name="my-leave-requests"),
    path("me/leave-requests/<int:request_id>/", MyLeaveRequestDetailAPI.as_view(), name="my-leave-request-detail"),
    path("me/leave-requests/<int:request_id>/cancel/", MyLeaveRequestCancelAPI.as_view(), name="my-leave-request-cancel"),

    # =====================================================
    # HR ADMINISTRATIVE LEAVE CONSOLE
    # =====================================================
    path("leave-requests/", LeaveRequestListAPI.as_view(), name="leave-request-list"),
    path("leave-requests/<int:request_id>/", LeaveRequestDetailAPI.as_view(), name="leave-request-detail"),
    path("leave-requests/<int:request_id>/approve/", LeaveRequestApproveAPI.as_view(), name="leave-request-approve"),
    path("leave-requests/<int:request_id>/reject/", LeaveRequestRejectAPI.as_view(), name="leave-request-reject"),
    path("leave-requests/<int:request_id>/cancel/", LeaveRequestCancelHRAPI.as_view(), name="leave-request-hr-cancel"),

    # =====================================================
    # PROFILE METRICS LOOKUPS (HR VIEW)
    # =====================================================
    path("employees/<int:membership_id>/leave-balances/", EmployeeLeaveBalancesAPI.as_view(), name="employee-leave-balances"),
    path("employees/<int:membership_id>/leave-requests/", EmployeeLeaveRequestsAPI.as_view(), name="employee-leave-requests"),

    # =====================================================
    # LEAVE TYPE POLICIES ENTITIES
    # =====================================================
    path("leave-types/", LeaveTypeListCreateAPI.as_view(), name="leave-type-list"),
    path("leave-types/<int:leave_type_id>/", LeaveTypeDetailUpdateDeleteAPI.as_view(), name="leave-type-detail"),

    # =====================================================
    # LEAVE BALANCE ADMINISTRATION
    # =====================================================
    path("leave-balances/", LeaveBalanceListAPI.as_view(), name="leave-balance-list"),
    path("leave-balances/<int:balance_id>/adjust/", LeaveBalanceAdjustAPI.as_view(), name="leave-balance-adjust"),
    path("leave-balances/allocate/", LeaveBalanceAllocateAPI.as_view(), name="leave-balance-allocate"),

    # =====================================================
    # ADVANCED HR ATTENDANCE OPERATION SYSTEM MIGRATIONS (NEW)
    # =====================================================
   path("hr-management/dashboard-summary/", HRDashboardSummaryAPIView.as_view(), name="hr-dashboard-summary"),
    path("hr-management/company-ledger/", HRCompanyLedgerAPIView.as_view(), name="hr-company-ledger"),
    
    path("hr-management/records/<int:record_id>/", HRAttendanceRecordDetailAPIView.as_view(), name="hr-record-detail"),

   path("hr-management/records/<int:record_id>/actions/check-in/", HRManualCheckInAPIView.as_view(), name="hr-action-check-in"),
    path("hr-management/records/<int:record_id>/actions/check-out/", HRManualCheckOutAPIView.as_view(), name="hr-action-check-out"),
    path("hr-management/records/<int:record_id>/actions/break-start/", HRManualBreakStartAPIView.as_view(), name="hr-action-break-start"),
    path("hr-management/records/<int:record_id>/actions/break-end/", HRManualBreakEndAPIView.as_view(), name="hr-action-break-end"),
    
    path("hr-management/records/<int:record_id>/actions/override-status/", HROverrideStatusAPIView.as_view(), name="hr-action-override-status"),
    path("hr-management/records/<int:record_id>/actions/finalize/", HRFinalizeRecordAPIView.as_view(), name="hr-action-finalize"),
    path("hr-management/records/<int:record_id>/actions/unlock/", HRUnlockRecordAPIView.as_view(), name="hr-action-unlock"),
    path("hr-management/records/<int:record_id>/actions/reprocess/", HRReprocessTimelineAPIView.as_view(), name="hr-action-reprocess"),
    path("hr-management/records/<int:record_id>/actions/recalculate/", HRReprocessTimelineAPIView.as_view(), name="hr-action-recalculate"), # Aligned aliases
    
    path("hr-management/records/<int:record_id>/actions/mark-review/", HRMarkNeedsReviewAPIView.as_view(), name="hr-action-mark-review"),
    path("hr-management/records/<int:record_id>/actions/clear-review/", HRClearReviewAPIView.as_view(), name="hr-action-clear-review"),    
    path("hr-management/corrections/manual-punch/", HRManualCorrectionAPIView.as_view(), name="hr-manual-correction"),
    
    path(
        "hr/dashboard/summary/", 
        HRDashboardSummaryAPIView.as_view(), 
        name="hr-attendance-dashboard-summary"
    ),

    path(
        "hr-management/employees/", 
        HREmployeeAttendanceDirectoryAPIView.as_view(), 
        name="hr-attendance-employee-directory"
    ),

    path(
        "hr-management/employees/<int:membership_id>/",
        HREmployeeAttendanceProfileAPIView.as_view(),
        name="hr-attendance-employee-profile-detail"
    ),


    path("hr/review/dashboard/", HRReviewDashboardAPIView.as_view(), name="hr-review-dashboard"),
    path("hr/review/", HRReviewQueueListAPIView.as_view(), name="hr-review-list"),
    path("hr/review/<int:pk>/", HRReviewItemDetailAPIView.as_view(), name="hr-review-detail"),
    
    path("hr/review/<int:pk>/assign/", HRReviewAssignAPIView.as_view(), name="hr-review-assign"),
    path("hr/review/<int:pk>/resolve/", HRReviewResolveAPIView.as_view(), name="hr-review-resolve"),
    path("hr/review/<int:pk>/reject/", HRReviewResolveAPIView.as_view(), name="hr-review-reject"),
    path("hr/review/<int:pk>/escalate/", HRReviewResolveAPIView.as_view(), name="hr-review-escalate"),
    path("hr/review/<int:pk>/note/", HRReviewNoteAPIView.as_view(), name="hr-review-note"),



    path("hr/reports/company/", HRCompanyReportSummaryAPIView.as_view(), name="hr-report-company-summary"),
    path("hr/reports/payroll/", HRPayrollAttendanceDatasetAPIView.as_view(), name="hr-report-payroll-ledger"),
    path("hr/reports/analytics/", HRReportAnalyticsAPIView.as_view(), name="hr-report-analytics-trends"),
    
    path("hr/reports/export/", HRReportExportTriggerAPIView.as_view(), name="hr-report-export-trigger"),
    path("hr/reports/history/", HRReportGenerationHistoryAPIView.as_view(), name="hr-report-export-history"),
    path("hr/reports/schedule/", HRReportAutomationSchedulingAPIView.as_view(), name="hr-report-schedule-rule"),

    ]