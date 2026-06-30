# apps/attendance/api/v1/serializers/hr_profile_serializers.py
from rest_framework import serializers
from apps.companies.models import Membership
from apps.attendance.models.daily_attendance import DailyAttendance

class HREmployeeProfileHeaderSerializer(serializers.ModelSerializer):
    membership_id = serializers.IntegerField(source="id")
    full_name = serializers.CharField(source="user.get_full_name")
    email = serializers.CharField(source="user.email")
    username = serializers.CharField(source="user.username")
    department_name = serializers.CharField(source="department.name", default="Unassigned")
    role_name = serializers.CharField(source="role.name", default="No Role Specified")
    joined_date = serializers.DateTimeField(source="created_at", format="%Y-%m-%d")

    class Meta:
        model = Membership
        fields = ["membership_id", "full_name", "email", "username", "department_name", "role_name", "is_active", "joined_date"]

class HRProfileSummaryCardsSerializer(serializers.Serializer):
    working_days = serializers.IntegerField()
    present = serializers.IntegerField()
    absent = serializers.IntegerField()
    leave = serializers.IntegerField()
    holiday = serializers.IntegerField()
    weekend = serializers.IntegerField()
    late_days = serializers.IntegerField()
    half_days = serializers.IntegerField()
    attendance_percentage = serializers.FloatField()
    average_check_in = serializers.CharField()
    average_check_out = serializers.CharField()
    average_work_hours = serializers.FloatField()
    average_break_hours = serializers.FloatField()
    total_work_hours = serializers.FloatField()
    total_overtime = serializers.FloatField()
    early_exits = serializers.IntegerField()
    missing_checkouts = serializers.IntegerField()
    needs_review = serializers.IntegerField()

class HRProfileTrendChartsSerializer(serializers.Serializer):
    daily_trends = serializers.JSONField()
    weekly_trends = serializers.JSONField()

class HRProfileAttendanceRecordRowSerializer(serializers.ModelSerializer):
    work_hours = serializers.SerializerMethodField()
    break_hours = serializers.SerializerMethodField()
    early_exit_minutes = serializers.IntegerField(source="early_exit_minutes_count", default=0, read_only=True)

    class Meta:
        model = DailyAttendance
        fields = [
            "id", "attendance_date", "attendance_status", "first_check_in_at", "last_check_out_at",
            "work_hours", "break_hours", "late_minutes", "early_exit_minutes", "overtime_minutes",
            "needs_review", "review_reason", "is_holiday", "is_weekend", "is_leave", "is_auto_closed", "source"
        ]

    def get_work_hours(self, obj: DailyAttendance) -> float:
        return round(obj.total_work_minutes / 60.0, 2)

    def get_break_hours(self, obj: DailyAttendance) -> float:
        return round(obj.total_break_minutes / 60.0, 2)