from django.urls import path

# Core Work Schedule Management Views
from apps.attendance.api.v1.views.company_work_schedule_api import (
    CompanyWorkScheduleAPI,
    CompanyWorkScheduleDetailAPI,
    CompanyWorkScheduleActivationAPI,
)

# Core Holiday CRUD & Listing Views
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
]