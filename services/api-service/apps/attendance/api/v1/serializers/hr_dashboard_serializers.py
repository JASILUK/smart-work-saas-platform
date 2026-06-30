# apps/attendance/api/v1/serializers/hr_dashboard_serializers.py
from rest_framework import serializers
from apps.attendance.models.daily_attendance import DailyAttendance
from apps.attendance.models.attendance_event import AttendanceEvent

class HRDashboardOverviewCardSerializer(serializers.Serializer):
    total_employees = serializers.IntegerField()
    present = serializers.IntegerField()
    currently_working = serializers.IntegerField()
    checked_out = serializers.IntegerField()
    not_checked_in = serializers.IntegerField()
    on_leave = serializers.IntegerField()
    absent = serializers.IntegerField()
    late = serializers.IntegerField()
    early_exit = serializers.IntegerField()
    missing_checkout = serializers.IntegerField()
    needs_review = serializers.IntegerField()
    company_attendance_percentage = serializers.FloatField()

class HRDashboardDepartmentItemSerializer(serializers.Serializer):
    department_id = serializers.IntegerField()
    department_name = serializers.CharField()
    employee_count = serializers.IntegerField()
    present = serializers.IntegerField()
    currently_working = serializers.IntegerField()
    leave = serializers.IntegerField()
    absent = serializers.IntegerField()
    late = serializers.IntegerField()
    attendance_percentage = serializers.FloatField()
    review_count = serializers.IntegerField()

class HRDashboardShiftItemSerializer(serializers.Serializer):
    shift_id = serializers.IntegerField(allow_null=True)
    shift_name = serializers.CharField()
    assigned_employees = serializers.IntegerField()
    checked_in = serializers.IntegerField()
    working = serializers.IntegerField()
    completed = serializers.IntegerField()
    not_checked_in = serializers.IntegerField()
    late = serializers.IntegerField()

class HRDashboardLiveWorkerSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="membership.user.get_full_name", default="")
    username = serializers.CharField(source="membership.user.username")
    department_name = serializers.CharField(source="membership.department.name", default="Unassigned")
    shift_name = serializers.CharField(source="schedule_snapshot.shift_name", default="Standard Shift")
    working_duration_minutes = serializers.IntegerField(source="total_work_minutes")
    attendance_method = serializers.CharField(source="source")

    class Meta:
        model = DailyAttendance
        fields = [
            "id", "membership_id", "username", "employee_name", "department_name",
            "shift_name", "first_check_in_at", "working_duration_minutes",
            "attendance_method", "attendance_status"
        ]

class HRDashboardEventActivitySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="membership.user.get_full_name", default="")
    department_name = serializers.CharField(source="membership.department.name", default="Unassigned")
    shift_name = serializers.CharField(source="verification_payload.shift_name", default="Standard Shift")

    class Meta:
        model = AttendanceEvent
        fields = [
            "id", "membership_id", "employee_name", "department_name", "shift_name",
            "event_type", "event_time", "attendance_method", "notes"
        ]

class HRDashboardAlertNotificationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="membership.user.get_full_name", default="")
    department_name = serializers.CharField(source="membership.department.name", default="Unassigned")
    alert_type = serializers.SerializerMethodField()
    trigger_description = serializers.SerializerMethodField()

    class Meta:
        model = DailyAttendance
        fields = [
            "id", "membership_id", "employee_name", "department_name", "attendance_date",
            "alert_type", "trigger_description", "is_auto_closed", "needs_review"
        ]

    def get_alert_type(self, obj: DailyAttendance) -> str:
        if obj.is_auto_closed:
            return "AUTO_CLOSED_TIMESHEET"
        if obj.first_check_in_at and not obj.last_check_out_at:
            return "MISSING_SHIFT_CHECKOUT"
        return "CRITICAL_TIMELINE_CONFLICT"

    def get_trigger_description(self, obj: DailyAttendance) -> str:
        if obj.review_reason:
            return obj.review_reason
        if obj.auto_close_reason:
            return obj.auto_close_reason
        return "Flagged automatically: Tracking anomalies require human verification."

class HRDashboardSummaryResponseSerializer(serializers.Serializer):
    """
    Root presentation serializer that structures the dashboard modules.
    """
    overview = HRDashboardOverviewCardSerializer()
    department_summary = HRDashboardDepartmentItemSerializer(many=True)
    shift_summary = HRDashboardShiftItemSerializer(many=True)
    live_attendance = HRDashboardLiveWorkerSerializer(many=True)
    recent_activity = HRDashboardEventActivitySerializer(many=True)
    alerts = HRDashboardAlertNotificationSerializer(many=True)