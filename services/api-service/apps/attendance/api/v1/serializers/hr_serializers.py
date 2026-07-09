# apps/attendance/api/v1/serializers/hr_serializers.py
from rest_framework import serializers
from apps.attendance.models.daily_attendance import DailyAttendance
from apps.attendance.models.attendance_event import AttendanceEvent

class HRMinifiedUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="user.id")
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    username = serializers.CharField(source="user.username")
    email = serializers.CharField(source="user.email")

class HRMinifiedDepartmentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()

class HREmployeeDirectoryRecordSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    first_name = serializers.CharField(source="user.username")
    last_name = serializers.CharField(source="user.last_name")
    department = HRMinifiedDepartmentSerializer()
    job_title = serializers.CharField()
    work_mode = serializers.CharField()

class HRNestedTimelineEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceEvent
        fields = [
            "id",
            "event_type",
            "attendance_method",
            "event_time",
            "notes",
            "is_system_generated"
        ]

class HRDailyLedgerOutputSerializer(serializers.ModelSerializer):
    """
    Optimized serialization layout for the corporate data grid.
    Maps model names cleanly to clear runtime fields.
    """
    employee_details = HREmployeeDirectoryRecordSerializer(source="membership", read_only=True)
    finalized_by_details = HRMinifiedUserSerializer(source="finalized_by", read_only=True)
    clock_in = serializers.DateTimeField(source="first_check_in_at", read_only=True)
    clock_out = serializers.DateTimeField(source="last_check_out_at", read_only=True)
    total_working_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = DailyAttendance
        fields = [
            "id",
            "employee_details",
            "attendance_date",
            "attendance_status",
            "clock_in",
            "clock_out",
            "total_working_hours",
            "is_late",
            "needs_review",
            "finalized_at",
            "finalized_by_details",
            "review_reason"
        ]

    def get_total_working_hours(self, obj: DailyAttendance) -> float:
        return round(obj.total_work_minutes / 60.0, 2)

class HRRecordDetailResponseSerializer(serializers.ModelSerializer):
    """
    Comprehensive serialization graph designed for fine-grained analytical panels.
    """
    employee_details = HREmployeeDirectoryRecordSerializer(source="membership", read_only=True)
    finalized_by_details = HRMinifiedUserSerializer(source="finalized_by", read_only=True)
    clock_in = serializers.DateTimeField(source="first_check_in_at", read_only=True)
    clock_out = serializers.DateTimeField(source="last_check_out_at", read_only=True)
    total_working_hours = serializers.SerializerMethodField()
    historical_events = serializers.SerializerMethodField()

    class Meta:
        model = DailyAttendance
        fields = [
            "id",
            "employee_details",
            "attendance_date",
            "attendance_status",
            "clock_in",
            "clock_out",
            "total_working_hours",
            "is_late",
            "needs_review",
            "finalized_at",
            "finalized_by_details",
            "historical_events",
            "review_reason",
            "total_break_minutes",
            "overtime_minutes",
            "late_minutes",
            "early_exit_minutes"
        ]

    def get_total_working_hours(self, obj: DailyAttendance) -> float:
        return round(obj.total_work_minutes / 60.0, 2)

    def get_historical_events(self, obj: DailyAttendance) -> list:
        # Uses the corrected prefetch manager name directly from cache memories safely
        events = obj.membership.attendance_events.filter(
            event_time__date=obj.attendance_date
        ).order_by("event_time")
        return HRNestedTimelineEventSerializer(events, many=True).data

class HRManualPunchInjectionSerializer(serializers.Serializer):
    membership_id = serializers.IntegerField(required=True)
    attendance_date = serializers.DateField(required=True)
    event_type = serializers.CharField(max_length=50, required=True)
    event_time = serializers.DateTimeField(required=True)
    reason = serializers.CharField(max_length=1000, required=True, min_length=5)

class HRStandardActionPayloadSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, required=True, min_length=5)