# apps/attendance/api/v1/serializers/hr_record_detail_serializers.py
from rest_framework import serializers
from apps.attendance.models.daily_attendance import DailyAttendance
from apps.attendance.models.attendance_event import AttendanceEvent
from apps.attendance.models.employee_attendance_override import EmployeeAttendanceOverride

class HRRecordMinifiedUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="user.id")
    full_name = serializers.CharField(source="user.get_full_name")
    email = serializers.CharField(source="user.email")

class HRRecordHeaderSerializer(serializers.ModelSerializer):
    membership_id = serializers.IntegerField(source="membership.id")
    employee_name = serializers.CharField(source="membership.user.get_full_name")
    avatar_url = serializers.SerializerMethodField()
    department_name = serializers.CharField(source="membership.department.name", default="Unassigned")
    finalized_by_name = serializers.CharField(source="finalized_by.user.get_full_name", default=None)

    class Meta:
        model = DailyAttendance
        fields = [
            "id", "attendance_date", "membership_id", "employee_name", "avatar_url",
            "department_name", "attendance_status", "needs_review", "finalized_at", "finalized_by_name"
        ]

    def get_avatar_url(self, obj: DailyAttendance) -> str:
        return f"https://ui-avatars.com/api/?name={obj.membership.user.first_name}+{obj.membership.user.last_name}&background=random"

class HRRecordSummarySerializer(serializers.ModelSerializer):
    working_hours = serializers.SerializerMethodField()
    break_hours = serializers.SerializerMethodField()
    overtime_hours = serializers.SerializerMethodField()

    class Meta:
        model = DailyAttendance
        fields = [
            "first_check_in_at", "last_check_out_at", "working_hours", "break_hours",
            "late_minutes", "early_exit_minutes", "overtime_hours", "required_work_minutes", "source"
        ]

    def get_working_hours(self, obj: DailyAttendance) -> float:
        return round(obj.total_work_minutes / 60.0, 2)

    def get_break_hours(self, obj: DailyAttendance) -> float:
        return round(obj.total_break_minutes / 60.0, 2)

    def get_overtime_hours(self, obj: DailyAttendance) -> float:
        return round(obj.overtime_minutes / 60.0, 2)

class HRRecordFlagsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyAttendance
        fields = [
            "is_present", "is_absent", "is_leave", "is_half_day", 
            "is_holiday", "is_weekend", "is_early_exit", "is_auto_closed", "needs_review"
        ]

class HRRecordReviewMetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyAttendance
        fields = ["needs_review", "review_reason", "auto_close_reason", "created_at", "updated_at"]

class HRRecordTimelineEventSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source="location.name", default=None)
    instigated_by = serializers.CharField(source="created_by.user.get_full_name", default="System Engine")
    telemetry = serializers.JSONField(source="verification_payload")

    class Meta:
        model = AttendanceEvent
        fields = [
            "id", "event_type", "event_time", "attendance_method", "location_name",
            "telemetry", "is_system_generated", "notes", "instigated_by"
        ]

class HRRecordAuditTrailSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="override_by.user.get_full_name", default="System Workflow")

    class Meta:
        model = EmployeeAttendanceOverride
        fields = ["id", "actor_name", "field_name", "old_value", "new_value", "reason", "created_at"]

class HRRecordAllowedActionsSerializer(serializers.Serializer):
    can_finalize = serializers.BooleanField()
    can_unlock = serializers.BooleanField()
    can_reprocess = serializers.BooleanField()
    can_manual_correction = serializers.BooleanField()
    can_checkin_override = serializers.BooleanField()
    can_checkout_override = serializers.BooleanField()

class ComprehensiveAttendanceRecordDetailSerializer(serializers.Serializer):
    """
    Root composition serializer structuring child components into a unified payload graph.
    """
    header = HRRecordHeaderSerializer(source="record")
    summary = HRRecordSummarySerializer(source="record")
    flags = HRRecordFlagsSerializer(source="record")
    review_info = HRRecordReviewMetaSerializer(source="record")
    schedule_snapshot = serializers.JSONField(source="record.schedule_snapshot")
    policy_snapshot = serializers.JSONField(source="record.policy_snapshot")
    timeline = HRRecordTimelineEventSerializer(many=True)
    audit_history = HRRecordAuditTrailSerializer(many=True)
    allowed_actions = HRRecordAllowedActionsSerializer()