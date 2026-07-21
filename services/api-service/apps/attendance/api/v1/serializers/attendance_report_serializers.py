# apps/attendance/api/v1/serializers/attendance_report_serializers.py
"""
Attendance Report Serializers Layer

Translates annotated database objects down into a scannable, standardized payload structure.
"""

from rest_framework import serializers
from apps.companies.models import Membership


class AttendanceReportRowSerializer(serializers.ModelSerializer):
    """
    Serializes optimized enterprise payroll ledger rows.
    """
    membership_id = serializers.IntegerField(source="id")
    employee_name = serializers.CharField(source="user.username")
    employee_avatar = serializers.SerializerMethodField()
    department = serializers.CharField(source="department.name", default="Unassigned")
    
    # Annotated metric properties fields mapped from backend query parameters
    present_days = serializers.IntegerField()
    absent_days = serializers.IntegerField()
    leave_days = serializers.IntegerField()
    holiday_days = serializers.IntegerField()
    weekend_days = serializers.IntegerField()
    late_count = serializers.IntegerField()
    
    # ✅ FIXED: Removed redundant source argument to satisfy DRF's assertion guard
    attendance_percentage = serializers.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        coerce_to_string=False
    )
    
    total_work_hours = serializers.FloatField()
    overtime_hours = serializers.FloatField()
    needs_review = serializers.BooleanField()

    class Meta:
        model = Membership
        fields = [
            "membership_id", "employee_name", "employee_avatar", "department", "job_title",
            "present_days", "absent_days", "leave_days", "holiday_days", "weekend_days",
            "late_count", "attendance_percentage", "total_work_hours", "overtime_hours", "needs_review"
        ]

    def get_employee_avatar(self, obj: Membership) -> str:
        """ Formulates baseline avatar asset references via user parameter properties string blocks """
        first = obj.user.first_name or ""
        last = obj.user.last_name or obj.user.username
        return f"https://ui-avatars.com/api/?name={first}+{last}&background=random"