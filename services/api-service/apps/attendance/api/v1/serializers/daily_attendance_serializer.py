from rest_framework import serializers
from apps.attendance.models.daily_attendance import DailyAttendance


class DailyAttendanceListSerializer(serializers.ModelSerializer):
    employee_username = serializers.CharField(source="membership.user.username", read_only=True)
    department_name = serializers.CharField(source="membership.department.name", read_only=True, default=None)

    class Meta:
        model = DailyAttendance
        fields = ["id", "attendance_date", "employee_username", "department_name", "attendance_status", "total_work_minutes", "is_late", "is_early_exit", "needs_review"]
        read_only_fields = fields


class DailyAttendanceDetailSerializer(serializers.ModelSerializer):
    employee_username = serializers.CharField(source="membership.user.username", read_only=True)
    employee_email = serializers.CharField(source="membership.user.email", read_only=True)
    finalizer_username = serializers.CharField(source="finalized_by.user.username", read_only=True, default=None)

    class Meta:
        model = DailyAttendance
        fields = [
            "id", "attendance_date", "employee_username", "employee_email",
            "schedule_snapshot", "policy_snapshot", "first_check_in_at", "last_check_out_at",
            "total_work_minutes", "total_break_minutes", "required_work_minutes",
            "overtime_minutes", "late_minutes", "early_exit_minutes", "attendance_status",
            "is_present", "is_half_day", "is_absent", "is_late", "is_early_exit",
            "is_auto_closed", "auto_close_reason", "needs_review", "review_reason",
            "finalized_at", "finalizer_username", "source", "created_at", "updated_at"
        ]
        read_only_fields = fields


class DailyAttendanceReprocessSerializer(serializers.Serializer):
    membership_id = serializers.IntegerField(required=True)
    target_date = serializers.DateField(required=True)


class DailyAttendanceFinalizeSerializer(serializers.Serializer):
    record_id = serializers.IntegerField(required=True)