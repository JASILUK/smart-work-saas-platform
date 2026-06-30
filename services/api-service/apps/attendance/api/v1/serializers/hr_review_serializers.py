# apps/attendance/api/v1/serializers/hr_review_serializers.py
from rest_framework import serializers
from apps.attendance.models.daily_attendance import DailyAttendance

class HRReviewQueueDashboardSerializer(serializers.Serializer):
    total_pending_review = serializers.IntegerField()
    high_priority_alerts = serializers.IntegerField()
    auto_closed_sheets = serializers.IntegerField()
    missing_checkouts = serializers.IntegerField()
    resolved_today_count = serializers.IntegerField()

class HRReviewQueueRowSerializer(serializers.ModelSerializer):
    record_id = serializers.IntegerField(source="id")
    employee_name = serializers.CharField(source="membership.user.get_full_name")
    department_name = serializers.CharField(source="membership.department.name", default="Unassigned")
    anomaly_type = serializers.CharField(source="computed_anomaly_type")
    priority = serializers.CharField(source="computed_priority")
    current_reviewer = serializers.CharField(source="finalized_by.user.get_full_name", default="Unassigned")
    review_status = serializers.CharField(source="computed_review_status")

    class Meta:
        model = DailyAttendance
        fields = [
            "record_id", "employee_name", "department_name", "attendance_date", "attendance_status",
            "anomaly_type", "priority", "review_reason", "current_reviewer", "review_status", "created_at"
        ]

class HRReviewActionInputSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, required=True, min_length=5)

class HRReviewAssignmentInputSerializer(HRReviewActionInputSerializer):
    reviewer_id = serializers.IntegerField(required=True)