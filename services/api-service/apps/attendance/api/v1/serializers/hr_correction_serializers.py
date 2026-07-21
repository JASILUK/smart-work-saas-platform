# apps/attendance/api/v1/serializers/hr_correction_serializers.py
"""
HR Operational Correction View Input Payload Schemas
"""

from rest_framework import serializers
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceEventTypes


class HRAttendanceEventCorrectionSerializer(serializers.Serializer):
    """
    Enforces runtime format mapping structures for administrative manual submissions.
    """
    membership_id = serializers.IntegerField(required=True)
    target_date = serializers.DateField(required=True)
    event_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    event_type = serializers.ChoiceField(choices=AttendanceEventTypes.choices, required=False, allow_null=True, default=None)
    event_time = serializers.DateTimeField(required=True)
    notes = serializers.CharField(required=True, min_length=5, max_length=1000)

    def validate(self, attrs):
        # Guarantee incoming logic rules can be satisfied based on payload contexts
        if not attrs.get("event_id") and not attrs.get("event_type"):
            raise serializers.ValidationError(
                {"event_type": "An explicit choice code identifier mapping is required when adding a new action track entry."}
            )
        return attrs