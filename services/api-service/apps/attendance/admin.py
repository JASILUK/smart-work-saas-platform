from django.contrib import admin
from apps.attendance.models.company_attendance_default import CompanyAttendanceDefault
from apps.attendance.models.attendance_access_rule import AttendanceAccessRule
from apps.attendance.models.employee_attendance_override import EmployeeAttendanceOverride

from apps.attendance.models.company_face_policy import CompanyFaceEnrollmentPolicy
from apps.attendance.models.face_enrollment import FaceEnrollment
from apps.attendance.models.holiday import Holiday
from apps.attendance.models.leave import LeaveBalance, LeaveType


# Register your models here.

admin.site.register(Holiday)

admin.site.register(LeaveType)


@admin.register(CompanyFaceEnrollmentPolicy)
class CompanyFaceEnrollmentPolicyAdmin(admin.ModelAdmin):
    list_display = ["company", "policy_type", "is_active", "updated_at"]
    list_filter = ["is_active", "policy_type"]
    search_fields = ["company__name"]


@admin.register(FaceEnrollment)
class FaceEnrollmentAdmin(admin.ModelAdmin):
    list_display = ["membership", "company", "status", "enrollment_source", "liveness_verified", "approved_at"]
    list_filter = ["status", "enrollment_source", "liveness_verified", "company"]
    search_fields = ["membership__user__username", "membership__user__email", "company__name"]
    
    # Secure Write-Only Audit Restrictions: Never drop or display large array values on list page frames
    readonly_fields = ["embedding", "approved_at", "approved_by", "revoked_at", "revoked_by"]




@admin.register(CompanyAttendanceDefault)
class CompanyAttendanceDefaultAdmin(admin.ModelAdmin):
    list_display = ["company", "validation_mode", "is_active", "created_at"]
    list_filter = ["is_active", "validation_mode"]
    search_fields = ["company__name"]
    filter_horizontal = ["allowed_methods", "allowed_locations"]


@admin.register(AttendanceAccessRule)
class AttendanceAccessRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "scope_type", "work_mode", "department", "priority", "is_active"]
    list_filter = ["is_active", "scope_type", "work_mode", "company"]
    search_fields = ["name", "company__name", "department__name"]
    filter_horizontal = ["allowed_methods", "allowed_locations"]


@admin.register(EmployeeAttendanceOverride)
class EmployeeAttendanceOverrideAdmin(admin.ModelAdmin):
    list_display = ["membership", "company", "validation_mode", "is_active", "updated_at"]
    list_filter = ["is_active", "validation_mode", "company"]
    search_fields = ["membership__user__username", "membership__user__email", "company__name", "reason"]
    filter_horizontal = ["allowed_methods", "allowed_locations"]


