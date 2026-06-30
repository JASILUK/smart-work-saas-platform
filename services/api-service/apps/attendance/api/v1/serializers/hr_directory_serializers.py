# apps/attendance/api/v1/serializers/hr_directory_serializers.py
from rest_framework import serializers
from apps.companies.models import Membership

class HREmployeeDirectoryRowSerializer(serializers.ModelSerializer):
    """
    Serializes a single employee directory row, pulling annotated database properties 
    efficiently without executing hidden sub-queries.
    """
    membership_id = serializers.IntegerField(source="id")
    employee_name = serializers.SerializerMethodField()
    email = serializers.CharField(source="user.email", read_only=True)
    avatar_url = serializers.SerializerMethodField()
    department_name = serializers.CharField(source="department.name", default="Unassigned")
    role_name = serializers.CharField(source="role.name", default="No Role")
    
    # Annotated Time-Tracking variables mapped cleanly out of the select pass
    attendance_record_id = serializers.IntegerField(source="db_record_id", read_only=True)
    attendance_status = serializers.CharField(source="db_status", default="ABSENT")
    current_state = serializers.CharField(source="computed_current_state", read_only=True)
    
    first_check_in = serializers.DateTimeField(source="db_first_in", read_only=True)
    last_check_out = serializers.DateTimeField(source="db_last_out", read_only=True)
    
    working_duration_minutes = serializers.IntegerField(source="db_work_min", default=0)
    break_duration_minutes = serializers.IntegerField(source="db_break_min", default=0)
    late_minutes = serializers.IntegerField(source="db_late_min", default=0)
    overtime_minutes = serializers.IntegerField(source="db_ot_min", default=0)
    
    attendance_method = serializers.CharField(source="db_source", default="ENGINE")
    needs_review = serializers.BooleanField(source="db_needs_review", default=False)
    review_reason = serializers.CharField(source="db_review_reason", default="")
    is_auto_closed = serializers.BooleanField(source="db_auto_closed", default=False)
    
    shift_name = serializers.CharField(source="db_shift_name", default="Unassigned Shift")
    schedule_start = serializers.CharField(source="db_schedule_start", default="")
    schedule_end = serializers.CharField(source="db_schedule_end", default="")

    class Meta:
        model = Membership
        fields = [
            "membership_id", "employee_name", "email", "avatar_url", "department_name", 
            "role_name", "attendance_record_id", "shift_name", "attendance_status", 
            "current_state", "first_check_in", "last_check_out", "working_duration_minutes", 
            "break_duration_minutes", "late_minutes", "overtime_minutes", "attendance_method", 
            "needs_review", "review_reason", "is_auto_closed", "schedule_start", "schedule_end"
        ]

    def get_employee_name(self, obj: Membership) -> str:
        return f"{obj.user.first_name} {obj.user.last_name}".strip()

    def get_avatar_url(self, obj: Membership) -> str:
        # Reuses existing platform avatar lookups if available; falls back to a clean placeholder UI
        if hasattr(obj, "avatar") and obj.avatar:
            return obj.avatar.url
        return f"https://ui-avatars.com/api/?name={obj.user.first_name}+{obj.user.last_name}&background=random"