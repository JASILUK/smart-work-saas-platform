from apps.companies.models import Membership
from rest_framework import serializers
from apps.attendance.models.attendance_event import AttendanceEvent


class AttendanceEventListSerializer(serializers.ModelSerializer):
    employee_username = serializers.CharField(source="membership.user.username", read_only=True)

    class Meta:
        model = AttendanceEvent
        fields = ["id", "event_type", "attendance_method", "event_time", "membership", "employee_username"]
        read_only_fields = fields


class AttendanceEventDetailSerializer(serializers.ModelSerializer):
    employee_username = serializers.CharField(source="membership.user.username", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True, default=None)
    creator_username = serializers.CharField(source="created_by.user.username", read_only=True, default=None)

    class Meta:
        model = AttendanceEvent
        fields = [
            "id", "event_type", "attendance_method", "event_time", "membership", "employee_username",
            "location", "location_name", "verification_payload", "notes", "created_by", 
            "creator_username", "is_system_generated", "created_at"
        ]
        read_only_fields = fields


class GenericPunchIngestionSerializer(serializers.Serializer):
    attendance_method = serializers.CharField(required=True)
    latitude = serializers.FloatField(required=False, default=None)
    longitude = serializers.FloatField(required=False, default=None)
    face_verified = serializers.BooleanField(required=False, default=False)
    confidence = serializers.FloatField(required=False, default=1.0)
    biometric_log_id = serializers.IntegerField(required=False, default=None)


class ManualAttendanceAdjustmentSerializer(serializers.Serializer):
    membership = serializers.PrimaryKeyRelatedField(queryset=Membership.objects.all(), required=True)
    event_type = serializers.CharField(required=True)
    notes = serializers.CharField(required=True, allow_blank=False)