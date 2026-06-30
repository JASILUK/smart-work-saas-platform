from rest_framework import serializers
import datetime
from django.utils import timezone
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
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    department = HRMinifiedDepartmentSerializer()

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
    Pulls pre-fetched object properties directly without executing slow dynamic sub-queries.
    """
    employee_details = HREmployeeDirectoryRecordSerializer(source="membership", read_only=True)
    finalized_by_details = HRMinifiedUserSerializer(source="finalized_by", read_only=True)
    
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
            "finalized_by_details"
        ]

class HRRecordDetailResponseSerializer(serializers.ModelSerializer):
    """
    Comprehensive serialization graph designed for fine-grained analytical panels.
    """
    employee_details = HREmployeeDirectoryRecordSerializer(source="membership", read_only=True)
    finalized_by_details = HRMinifiedUserSerializer(source="finalized_by", read_only=True)
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
            "historical_events"
        ]

    def get_historical_events(self, obj: DailyAttendance) -> list:
        # Pull records safely from the parent instance's pre-fetched data array cache
        events = obj.company.attendanceevent_set.filter(
            membership=obj.membership,
            event_time__date=obj.attendance_date
        ).order_by("event_time")
        return HRNestedTimelineEventSerializer(events, many=True).data

class HRManualPunchInjectionSerializer(serializers.Serializer):
    membership_id = serializers.IntegerField(required=True)
    attendance_date = serializers.DateField(required=True)
    event_type = serializers.CharField(max_length=50, required=True)
    event_time = serializers.DateTimeField(required=True)
    reason = serializers.CharField(max_length=1000, required=True, min_length=5)

    def validate_attendance_date(self, value: datetime.date) -> datetime.date:
        if value > timezone.now().date():
            raise serializers.ValidationError("Corrections cannot be assigned to future dates.")
        return value

class HRStandardActionPayloadSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, required=True, min_length=5)