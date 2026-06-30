# apps/attendance/api/v1/serializers/hr_action_serializers.py
from rest_framework import serializers
from apps.attendance.models.daily_attendance import DailyAttendanceStatus

class HRBaseActionInputSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, required=True, min_length=5)

class HRManualPunchInputSerializer(HRBaseActionInputSerializer):
    event_time = serializers.DateTimeField(required=True)

class HROverrideStatusInputSerializer(HRBaseActionInputSerializer):
    target_status = serializers.ChoiceField(choices=DailyAttendanceStatus.choices, required=True)