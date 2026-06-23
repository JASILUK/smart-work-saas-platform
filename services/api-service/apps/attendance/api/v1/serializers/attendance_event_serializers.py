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
    """
    Secure serializer for all punch actions:
    check-in, check-out, break-out, break-in.
    
    Uses verification tokens instead of raw booleans.
    """
    attendance_method = serializers.CharField(required=True)
    
    # GPS verification token (from /verify/gps/)
    gps_verification_token = serializers.CharField(
        required=False, 
        allow_blank=True,
        help_text="Token from GPS verification API"
    )
    
    # Face verification token (from /verify/face/)
    face_verification_token = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Token from Face verification API"
    )
    
    # Biometric evidence
    biometric_log_id = serializers.IntegerField(
        required=False,
        default=None,
        help_text="Required for BIOMETRIC method"
    )
    
    # Manual attendance
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Required for MANUAL method"
    )
    
    # ─── DEPRECATED: Removed insecure fields ───
    # latitude = serializers.FloatField(...)  # REMOVED
    # longitude = serializers.FloatField(...)  # REMOVED
    # face_verified = serializers.BooleanField(...)  # REMOVED - NEVER trust frontend
    # confidence = serializers.FloatField(...)  # REMOVED
    
    def validate(self, data):
        method = data.get("attendance_method")
        
        # Validate method-specific required tokens
        if method in ["GPS_ONLY", "GPS_FACE"]:
            if not data.get("gps_verification_token"):
                raise serializers.ValidationError(
                    {"gps_verification_token": "GPS verification token is required."}
                )
        
        if method in ["FACE_ONLY", "GPS_FACE"]:
            if not data.get("face_verification_token"):
                raise serializers.ValidationError(
                    {"face_verification_token": "Face verification token is required."}
                )
        
        if method == "BIOMETRIC":
            if not data.get("biometric_log_id"):
                raise serializers.ValidationError(
                    {"biometric_log_id": "Biometric log ID is required."}
                )
        
        if method == "MANUAL":
            if not data.get("reason"):
                raise serializers.ValidationError(
                    {"reason": "Reason is required for manual attendance."}
                )
        
        return data

class ManualAttendanceAdjustmentSerializer(serializers.Serializer):
    membership = serializers.PrimaryKeyRelatedField(queryset=Membership.objects.all(), required=True)
    event_type = serializers.CharField(required=True)
    notes = serializers.CharField(required=True, allow_blank=False)