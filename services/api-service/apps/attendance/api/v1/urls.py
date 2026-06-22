from django.urls import path

# Core Work Schedule Management Views
from apps.attendance.api.v1.views.attendance_access_views import AttendanceAccessResolutionAPI, AttendanceAccessRuleDetailAPI, AttendanceAccessRuleListCreateAPI, CompanyAttendanceDefaultAPI, EmployeeAttendanceOverrideDetailAPI, EmployeeAttendanceOverrideListCreateAPI
from apps.attendance.api.v1.views.attendance_event_views import AttendanceBreakInAPI, AttendanceBreakOutAPI, AttendanceCheckInAPI, AttendanceCheckOutAPI, AttendanceEventDetailAPI, AttendanceEventListAPI, LiveAttendanceSummaryAPI, ManualAttendanceAPI
from apps.attendance.api.v1.views.attendance_location_views import ActivateAttendanceLocationAPI, AttendanceLocationDetailAPI, AttendanceLocationListCreateAPI
from apps.attendance.api.v1.views.biometric_log_views import BiometricLogDetailAPI, BiometricLogListAPI, ManualImportAPI, PushWebhookAPI
from apps.attendance.api.v1.views.biometric_views import BiometricDeviceActivateAPI, BiometricDeviceDetailAPI, BiometricDeviceListCreateAPI, BiometricEmployeeMappingActivateAPI, BiometricEmployeeMappingDetailAPI, BiometricEmployeeMappingListCreateAPI
from apps.attendance.api.v1.views.company_attendance_method_views import CompanyAttendanceMethodAPI, CompanyAttendanceMethodActionAPI
from apps.attendance.api.v1.views.company_work_schedule_api import (
    CompanyWorkScheduleAPI,
    CompanyWorkScheduleDetailAPI,
    CompanyWorkScheduleActivationAPI,
)

# Core Holiday CRUD & Listing Views
from apps.attendance.api.v1.views.daily_attendance_views import DailyAttendanceDetailAPI, DailyAttendanceFinalizeAPI, DailyAttendanceListAPI, DailyAttendanceReprocessAPI, DailyAttendanceReviewsAPI
from apps.attendance.api.v1.views.employee_dashboard_view import EmployeeDashboardAPIView
from apps.attendance.api.v1.views.face_enrollment_views import CompanyFaceEnrollmentPolicyAPI, EmployeeSelfEnrollmentAPI, FaceEnrollmentApproveAPI, FaceEnrollmentDetailAPI, FaceEnrollmentListAPI, FaceEnrollmentRejectAPI, FaceEnrollmentRevokeAPI, HRInstructionEnrollmentAPI
from apps.attendance.api.v1.views.holiday_views import (
    HolidayListCreateAPI,
    HolidayDetailAPI,
    HolidayImportAPI,
    HolidayPreviewAPI,
)

# Core Shift Management Views
from apps.attendance.api.v1.views.shift_views import (
    ShiftListCreateAPI,
    ShiftDetailAPI,
    ActivateShiftAPI,
    SetDefaultShiftAPI,
)

# Employee Shift Assignment Views
from apps.attendance.api.v1.views.employee_shift_assignemnt_view import (
    EmployeeShiftAssignmentListCreateAPI,
    EmployeeShiftAssignmentDetailAPI,
    EndEmployeeShiftAssignmentAPI,
    DeactivateEmployeeShiftAssignmentAPI,
    BulkAssignEmployeeShiftAPI,
    TransferEmployeeShiftAPI,
)

# Attendance Policy Administration Views
from apps.attendance.api.v1.views.attendance_policy_views import (
    AttendancePolicyDetailAPI,
    AttendancePolicyUpdateAPI,
    AttendancePolicyResetAPI,
)

# Namespace definition matching enterprise modular workspace patterns
app_name = "attendance"

urlpatterns = [
    # =====================================================
    # 1. COMPANY WORK SCHEDULE RULES
    # =====================================================
    # GET: View tenant defaults | POST: Initialize base policy rules
    path(
        "schedule/",
        CompanyWorkScheduleAPI.as_view(),
        name="company-schedule"
    ),
    
    # PATCH: Modify subset attributes of an active work schedule
    path(
        "schedule/detail/",
        CompanyWorkScheduleDetailAPI.as_view(),
        name="company-schedule-detail"
    ),
    
    # POST: Toggle the operational enforcement toggle (Activate / Deactivate)
    path(
        "schedule/activation/",
        CompanyWorkScheduleActivationAPI.as_view(),
        name="company-schedule-activation"
    ),

    # =====================================================
    # 2. HOLIDAY COMPLIANCE CRUD
    # =====================================================
    # GET: Lightweight sorted listing sheets | POST: Manual rule insertions by HR
    path(
        "holidays/", 
        HolidayListCreateAPI.as_view(), 
        name="holiday-list-create"
    ),
    
    # GET: Detailed record layout | PATCH: Edit targets | DELETE: Remove entry
    path(
        "holidays/<int:holiday_id>/", 
        HolidayDetailAPI.as_view(), 
        name="holiday-detail"
    ),

    # =====================================================
    # 3. EXTERNAL COMPLIANCE IMPORT PIPELINES
    # =====================================================
    # POST: Trigger high-performance, in-memory deduplication bulk imports
    path(
        "holidays/import/", 
        HolidayImportAPI.as_view(), 
        name="holiday-import"
    ),
    
    # POST: Safe read-only evaluation layer mapping provider outputs to front-end UI
    path(
        "holidays/import/preview/", 
        HolidayPreviewAPI.as_view(), 
        name="holiday-import-preview"
    ),

    # =====================================================
    # 4. REUSABLE SHIFT CONFIGURATIONS
    # =====================================================
    # GET: List active/inactive company shifts | POST: Create a fresh reusable shift
    path(
        "shifts/",
        ShiftListCreateAPI.as_view(),
        name="shift-list-create"
    ),

    # GET: Detailed view | PATCH: Dynamic field update | DELETE: Safe soft deactivation
    path(
        "shifts/<int:public_id>/",
        ShiftDetailAPI.as_view(),
        name="shift-detail"
    ),

    # POST: Reactivate an inactive or archived company shift profile
    path(
        "shifts/<int:public_id>/activate/",
        ActivateShiftAPI.as_view(),
        name="shift-activate"
    ),

    # POST: Set a reusable shift configuration as the fallback tenant schedule
    path(
        "shifts/<int:public_id>/set-default/",
        SetDefaultShiftAPI.as_view(),
        name="shift-set-default"
    ),

    # =====================================================
    # 5. EMPLOYEE SHIFT ASSIGNMENTS
    # =====================================================
    # GET: List historical shift assignment grids | POST: Assign single shift range
    path(
        "assignments/",
        EmployeeShiftAssignmentListCreateAPI.as_view(),
        name="assignment-list-create"
    ),

    # GET: Detailed assignment overview | PATCH: Safe boundary parameter modifications
    path(
        "assignments/<int:pk>/",
        EmployeeShiftAssignmentDetailAPI.as_view(),
        name="assignment-detail"
    ),

    # POST: Truncate a timeline by adding a definitive end date (effective_until)
    path(
        "assignments/<int:pk>/end/",
        EndEmployeeShiftAssignmentAPI.as_view(),
        name="assignment-end"
    ),

    # POST: Terminate a timeline and flag as inactive immediately
    path(
        "assignments/<int:pk>/deactivate/",
        DeactivateEmployeeShiftAssignmentAPI.as_view(),
        name="assignment-deactivate"
    ),

    # POST: Concurrently transition an employee to a new profile without gap intervals
    path(
        "assignments/<int:pk>/transfer/",
        TransferEmployeeShiftAPI.as_view(),
        name="assignment-transfer"
    ),

    # POST: Execute bulk onboarding roster sequences for multiple memberships
    path(
        "assignments/bulk-assign/",
        BulkAssignEmployeeShiftAPI.as_view(),
        name="assignment-bulk-assign"
    ),

    # =====================================================
    # 6. ATTENDANCE INTERPRETATION POLICIES
    # =====================================================
    # GET: Fetch or initialize current company rules | PATCH: Modify baseline rules
    path(
        "policy/",
        AttendancePolicyDetailAPI.as_view(),
        name="attendance-policy-detail"
    ),
    
    path(
        "policy/update/",
        AttendancePolicyUpdateAPI.as_view(),
        name="attendance-policy-update"
    ),

    # POST: Revert localized tenant threshold changes back to system defaults
    path(
        "policy/reset/",
        AttendancePolicyResetAPI.as_view(),
        name="attendance-policy-reset"
    ),

    path(
            "methods/",
            CompanyAttendanceMethodAPI.as_view(),
            name="company-attendance-methods-overview",
        ),
    
    # Focused single-method toggle switch operations
    path(
        "methods/<str:method_name>/",
        CompanyAttendanceMethodActionAPI.as_view(),
        name="company-attendance-method-soft-delete",
    ),
    path(
        "methods/<str:method_name>/enable/",
        CompanyAttendanceMethodActionAPI.as_view(),
        name="company-attendance-method-enable",
    ),

    path(
        "locations/", 
        AttendanceLocationListCreateAPI.as_view(), 
        name="attendance-locations-list-create"
    ),

    path(
        "locations/<int:location_id>/", 
        AttendanceLocationDetailAPI.as_view(), 
        name="attendance-location-detail"
    ),

    path(
        "locations/<int:location_id>/activate/",
        ActivateAttendanceLocationAPI.as_view(), 
        name="attendance-location-activate"
    ),


    path("access/defaults/", CompanyAttendanceDefaultAPI.as_view(), name="attendance-access-defaults"),

    # Group Scope Structural Optimization Rules Endpoints
    path("access/rules/", AttendanceAccessRuleListCreateAPI.as_view(), name="attendance-access-rules-list-create"),
    path("access/rules/<int:rule_id>/", AttendanceAccessRuleDetailAPI.as_view(), name="attendance-access-rule-detail"),

    # Individual Employee Exceptions Profiles Endpoints
    path("access/overrides/", EmployeeAttendanceOverrideListCreateAPI.as_view(), name="attendance-access-overrides-list-create"),
    path("access/overrides/<int:override_id>/", EmployeeAttendanceOverrideDetailAPI.as_view(), name="attendance-access-override-detail"),

    # Real-Time Operational Resolution Matrix Engine Output Entrypoint
    path("access/resolve/", AttendanceAccessResolutionAPI.as_view(), name="attendance-access-resolve-profile"),



    path("face-enrollments/policy/", CompanyFaceEnrollmentPolicyAPI.as_view(), name="face-policy-management"),

    # Submission Action Triggers
    path("face-enrollments/self/", EmployeeSelfEnrollmentAPI.as_view(), name="face-self-enrollment"),
    path("face-enrollments/hr/", HRInstructionEnrollmentAPI.as_view(), name="face-hr-enrollment"),

    # Data Monitoring Queues and Action Targets
    path("face-enrollments/", FaceEnrollmentListAPI.as_view(), name="face-enrollments-list"),
    path("face-enrollments/<int:pk>/", FaceEnrollmentDetailAPI.as_view(), name="face-enrollment-detail"),
    path("face-enrollments/<int:pk>/approve/", FaceEnrollmentApproveAPI.as_view(), name="face-enrollment-approve"),
    path("face-enrollments/<int:pk>/reject/", FaceEnrollmentRejectAPI.as_view(), name="face-enrollment-reject"),
    path("face-enrollments/<int:pk>/revoke/", FaceEnrollmentRevokeAPI.as_view(), name="face-enrollment-revoke"),


    path("biometric/devices/", BiometricDeviceListCreateAPI.as_view(), name="biometric-devices-list-create"),
    path("biometric/devices/<int:pk>/", BiometricDeviceDetailAPI.as_view(), name="biometric-device-detail"),
    path("biometric/devices/<int:pk>/activate/", BiometricDeviceActivateAPI.as_view(), name="biometric-device-activate"),

    # Users Sync Hardware Mapping Allocators Endpoints
    path("biometric/mappings/", BiometricEmployeeMappingListCreateAPI.as_view(), name="biometric-mappings-list-create"),
    path("biometric/mappings/<int:pk>/", BiometricEmployeeMappingDetailAPI.as_view(), name="biometric-mapping-detail"),
    path("biometric/mappings/<int:pk>/activate/", BiometricEmployeeMappingActivateAPI.as_view(), name="biometric-mapping-activate"),

    path("biometric/logs/", BiometricLogListAPI.as_view(), name="biometric-logs-list"),
    path("biometric/logs/<int:pk>/", BiometricLogDetailAPI.as_view(), name="biometric-log-detail"),
    
    # Ingestion Control Channels Interface Actions
    path("biometric/logs/import/", ManualImportAPI.as_view(), name="biometric-manual-import"),
    path("biometric/webhooks/push/", PushWebhookAPI.as_view(), name="biometric-device-push-webhook"),


    # Core operational tracking endpoints
    path("punch/check-in/", AttendanceCheckInAPI.as_view(), name="attendance-check-in"),
    path("punch/break-out/", AttendanceBreakOutAPI.as_view(), name="attendance-break-out"),
    path("punch/break-in/", AttendanceBreakInAPI.as_view(), name="attendance-break-in"),
    path("punch/check-out/", AttendanceCheckOutAPI.as_view(), name="attendance-check-out"),

    # Reporting and administration ledger lists
    path("punch/events/", AttendanceEventListAPI.as_view(), name="attendance-events-tracker-list"),
    path("punch/events/<int:pk>/", AttendanceEventDetailAPI.as_view(), name="attendance-event-tracker-detail"),
    path("punch/manual-override/", ManualAttendanceAPI.as_view(), name="attendance-manual-override-adjust"),
    path("punch/live-summary/", LiveAttendanceSummaryAPI.as_view(), name="attendance-live-dashboard-summary"),


    # Daily Finalization Engine Pipeline Routes
    path("daily/", DailyAttendanceListAPI.as_view(), name="daily-attendance-summary-list"),
    path("daily/<int:pk>/", DailyAttendanceDetailAPI.as_view(), name="daily-attendance-summary-detail"),
    path("daily/reprocess/", DailyAttendanceReprocessAPI.as_view(), name="daily-attendance-pipeline-reprocess"),
    path("daily/finalize/", DailyAttendanceFinalizeAPI.as_view(), name="daily-attendance-sheet-finalize"),
    path("daily/reviews/", DailyAttendanceReviewsAPI.as_view(), name="daily-attendance-exceptions-reviews"),


    path(
        "dashboard/",
        EmployeeDashboardAPIView.as_view(),
        name="attendance-dashboard",
    ),


]