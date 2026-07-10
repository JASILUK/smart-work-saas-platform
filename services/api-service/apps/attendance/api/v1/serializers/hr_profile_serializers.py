# apps/attendance/api/v1/serializers/hr_profile_serializers.py
"""
HR Profile Serializers

Dedicated, single-responsibility serializers for each section of the
Employee Attendance Profile response. No overloaded serializers.
"""

from rest_framework import serializers
from apps.companies.models import Membership
from apps.attendance.models.daily_attendance import DailyAttendance


# =============================================================================
# Employee Header Serializer
# =============================================================================

class HREmployeeProfileHeaderSerializer(serializers.ModelSerializer):
    """
    Serializes employee profile header metadata.

    Fields:
        membership_id, full_name, username, email, department_name, role_name,
        employment_status, joined_date, avatar_url,
        current_attendance_status, current_attendance_source
    """
    membership_id = serializers.IntegerField(source="id", read_only=True)
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    department_name = serializers.CharField(
        source="department.name", default="Unassigned", read_only=True
    )
    role_name = serializers.CharField(
        source="role.name", default="No Role Specified", read_only=True
    )
    employment_status = serializers.SerializerMethodField()
    joined_date = serializers.DateTimeField(
        source="joined_at", format="%Y-%m-%d", read_only=True
    )
    avatar_url = serializers.SerializerMethodField()
    current_attendance_status = serializers.CharField(
        default=None, read_only=True
    )
    current_attendance_source = serializers.CharField(
        default=None, read_only=True
    )

    class Meta:
        model = Membership
        fields = [
            "membership_id",
            "full_name",
            "username",
            "email",
            "department_name",
            "role_name",
            "employment_status",
            "joined_date",
            "avatar_url",
            "current_attendance_status",
            "current_attendance_source",
        ]

    def get_avatar_url(self, obj: Membership) -> str:
        """Returns the user's avatar URL if available, else empty string."""
        if hasattr(obj.user, "avatar") and obj.user.avatar:
            return obj.user.avatar.url if hasattr(obj.user.avatar, "url") else str(obj.user.avatar)
        return ""

    def get_employment_status(self, obj: Membership) -> str:
        """Returns employment status based on is_active flag."""
        return "Active" if obj.is_active else "Inactive"


# =============================================================================
# Summary Serializer
# =============================================================================

class HRProfileSummarySerializer(serializers.Serializer):
    """
    Serializes period-level attendance summary KPIs.

    All fields are read-only and computed by AttendanceSummarySelector.
    """
    # Day counters
    calendar_days = serializers.IntegerField()
    working_days = serializers.IntegerField()
    present_days = serializers.IntegerField()
    absent_days = serializers.IntegerField()
    half_days = serializers.IntegerField()
    late_days = serializers.IntegerField()
    early_exit_days = serializers.IntegerField()
    leave_days = serializers.IntegerField()
    holiday_days = serializers.IntegerField()
    weekend_days = serializers.IntegerField()

    # Exception counters
    needs_review = serializers.IntegerField()
    missing_checkout = serializers.IntegerField()
    auto_closed = serializers.IntegerField()

    # Percentage
    attendance_percentage = serializers.FloatField()

    # Average times
    average_check_in = serializers.CharField()
    average_check_out = serializers.CharField()
    average_work_hours = serializers.FloatField()
    average_break_hours = serializers.FloatField()

    # Totals
    total_work_hours = serializers.FloatField()
    total_break_hours = serializers.FloatField()
    total_overtime_hours = serializers.FloatField()
    late_minutes = serializers.IntegerField()
    overtime_minutes = serializers.IntegerField()


# =============================================================================
# Trend Charts Serializer
# =============================================================================

class HRProfileTrendChartsSerializer(serializers.Serializer):
    """
    Serializes the complete trend charts bundle.

    Each trend array is already frontend-ready (no transformation needed).
    """
    daily = serializers.ListField(child=serializers.DictField(), read_only=True)
    weekly = serializers.ListField(child=serializers.DictField(), read_only=True)
    monthly = serializers.ListField(child=serializers.DictField(), read_only=True)
    late_trend = serializers.ListField(child=serializers.DictField(), read_only=True)
    work_hours_trend = serializers.ListField(child=serializers.DictField(), read_only=True)
    overtime_trend = serializers.ListField(child=serializers.DictField(), read_only=True)


# =============================================================================
# Status Distribution Serializer
# =============================================================================

class HRProfileStatusDistributionSerializer(serializers.Serializer):
    """
    Serializes a single status distribution entry.
    """
    status = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()


# =============================================================================
# Attendance Record Row Serializer
# =============================================================================

class HRProfileAttendanceRecordRowSerializer(serializers.ModelSerializer):
    """
    Serializes individual attendance records for the paginated list.

    Computes work_hours and break_hours from minute fields.
    Maps early_exit_minutes from the model field.
    """
    work_hours = serializers.SerializerMethodField()
    break_hours = serializers.SerializerMethodField()
    early_exit_minutes = serializers.IntegerField(
        read_only=True,
    )
    check_in = serializers.DateTimeField(
        source="first_check_in_at", format="%Y-%m-%d %H:%M:%S", read_only=True
    )
    check_out = serializers.DateTimeField(
        source="last_check_out_at", format="%Y-%m-%d %H:%M:%S", read_only=True
    )
    finalized = serializers.SerializerMethodField()

    class Meta:
        model = DailyAttendance
        fields = [
            "id",
            "attendance_date",
            "attendance_status",
            "check_in",
            "check_out",
            "work_hours",
            "break_hours",
            "late_minutes",
            "early_exit_minutes",
            "overtime_minutes",
            "needs_review",
            "review_reason",
            "is_auto_closed",
            "is_holiday",
            "is_weekend",
            "is_leave",
            "source",
            "finalized",
        ]

    def get_work_hours(self, obj: DailyAttendance) -> float:
        return round(obj.total_work_minutes / 60.0, 2)

    def get_break_hours(self, obj: DailyAttendance) -> float:
        return round(obj.total_break_minutes / 60.0, 2)

    def get_finalized(self, obj: DailyAttendance) -> bool:
        return obj.finalized_at is not None