# apps/attendance/api/v1/serializers/hr_review_serializers.py
from rest_framework import serializers
from apps.attendance.models.daily_attendance import DailyAttendance

class HRReviewDashboardMetricsSerializer(serializers.Serializer):
    review_count = serializers.IntegerField(read_only=True)
    auto_closed_count = serializers.IntegerField(read_only=True)
    missing_checkout_count = serializers.IntegerField(read_only=True)
    duplicate_punches_count = serializers.IntegerField(read_only=True)
    unresolved_count = serializers.IntegerField(read_only=True)
    today_review_count = serializers.IntegerField(read_only=True)

class HRReviewQueueRowSerializer(serializers.ModelSerializer):
    employee_id = serializers.IntegerField(source="membership.id", read_only=True)
    employee_name = serializers.CharField(source="membership.user.get_full_name", read_only=True)
    department_name = serializers.CharField(source="membership.department.name", default="Unassigned", read_only=True)
    
    class Meta:
        model = DailyAttendance
        fields = [
            "id", "employee_id", "employee_name", "department_name", 
            "attendance_date", "attendance_status", "review_reason", 
            "first_check_in_at", "last_check_out_at", "is_auto_closed", "created_at"
        ]
        read_only_fields = fields

class HRReviewResolveInputSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=5, max_length=1000, required=True, allow_blank=False)

class HRReviewNoteInputSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=5, max_length=2000, required=True, allow_blank=False)