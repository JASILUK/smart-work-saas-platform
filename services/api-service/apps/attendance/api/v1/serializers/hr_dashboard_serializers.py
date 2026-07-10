# apps/attendance/api/v1/serializers/hr_dashboard_serializers.py

from rest_framework import serializers
from apps.attendance.models.attendance_event import AttendanceEvent


class CompanyWorkforceSummarySerializer(serializers.Serializer):
    total_employees = serializers.IntegerField()
    scheduled_today = serializers.IntegerField()
    checked_in = serializers.IntegerField()
    currently_working = serializers.IntegerField()
    on_break = serializers.IntegerField()
    checked_out = serializers.IntegerField()
    # FIXED: Add on_leave field
    on_leave = serializers.IntegerField(default=0)
    absent_until_now = serializers.IntegerField()
    attendance_percentage = serializers.FloatField()
    is_holiday = serializers.BooleanField()
    is_off_day = serializers.BooleanField()


class DepartmentSummarySerializer(serializers.Serializer):
    department_id = serializers.IntegerField()
    department_name = serializers.CharField()
    employees_count = serializers.IntegerField()
    working_count = serializers.IntegerField()
    break_count = serializers.IntegerField()
    checked_out_count = serializers.IntegerField()
    leave_count = serializers.IntegerField()
    absent_count = serializers.IntegerField()
    not_started_count = serializers.IntegerField()
    attendance_percentage = serializers.FloatField()


class ShiftSummarySerializer(serializers.Serializer):
    """
    FIXED: Added leave_count field to match selector payload.
    """
    shift_id = serializers.IntegerField()
    shift_name = serializers.CharField()
    employees_count = serializers.IntegerField()
    working_count = serializers.IntegerField()
    break_count = serializers.IntegerField()
    checked_out_count = serializers.IntegerField()
    # FIXED: Add leave_count field
    leave_count = serializers.IntegerField(default=0)
    absent_count = serializers.IntegerField()
    late_count = serializers.IntegerField()


class LiveEmployeeStatusCardSerializer(serializers.Serializer):
    membership_id = serializers.IntegerField()
    full_name = serializers.CharField()
    avatar_url = serializers.URLField(allow_null=True)
    department_name = serializers.CharField()
    shift_name = serializers.CharField()
    last_event_type = serializers.CharField()
    last_event_time = serializers.DateTimeField()
    current_status = serializers.CharField()
    is_late = serializers.BooleanField()


class ActivityFeedEventRowSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="membership.user.get_full_name", read_only=True)
    department_name = serializers.CharField(source="membership.department.name", default="Unassigned", read_only=True)
    time = serializers.DateTimeField(source="event_time", read_only=True)
    method = serializers.CharField(source="attendance_method", read_only=True)
    event = serializers.CharField(source="event_type", read_only=True)

    class Meta:
        model = AttendanceEvent
        fields = ["id", "employee_name", "department_name", "event", "time", "method", "notes"]


class DashboardMetadataSerializer(serializers.Serializer):
    summary_date = serializers.DateField()
    generated_at = serializers.DateTimeField()
    timezone = serializers.CharField()
    company_name = serializers.CharField()


class MasterDashboardResponseGraphSerializer(serializers.Serializer):
    summary = CompanyWorkforceSummarySerializer()
    departments = DepartmentSummarySerializer(many=True)
    shift_distribution = ShiftSummarySerializer(many=True)
    live_workforce = LiveEmployeeStatusCardSerializer(many=True)
    activity_feed = ActivityFeedEventRowSerializer(many=True)
    metadata = DashboardMetadataSerializer()