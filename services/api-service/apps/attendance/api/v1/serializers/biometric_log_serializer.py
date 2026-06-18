from rest_framework import serializers
from apps.attendance.models.biometric_log import BiometricLog


class BiometricLogListSerializer(serializers.ModelSerializer):
    employee_username = serializers.CharField(source="membership.user.username", read_only=True, default=None)
    device_name = serializers.CharField(source="device.name", read_only=True, default=None)

    class Meta:
        model = BiometricLog
        fields = ["id", "membership", "employee_username", "device", "device_name", "device_user_id", "event_type", "punch_time", "processing_status", "source"]
        read_only_fields = fields


class BiometricLogDetailSerializer(serializers.ModelSerializer):
    employee_username = serializers.CharField(source="membership.user.username", read_only=True, default=None)
    device_name = serializers.CharField(source="device.name", read_only=True, default=None)

    class Meta:
        model = BiometricLog
        fields = [
            "id", "membership", "employee_username", "device", "device_name", 
            "device_user_id", "event_type", "punch_time", "device_log_id", 
            "source", "raw_payload", "sync_batch_id", "processing_status", 
            "processed_at", "failure_reason", "created_at", "updated_at"
        ]
        read_only_fields = fields


class SingleManualPunchSerializer(serializers.Serializer):
    device_user_id = serializers.CharField(max_length=100, required=True)
    punch_time = serializers.DateTimeField(required=True)
    event_type = serializers.CharField(max_length=20, required=False, default="UNKNOWN")


class ManualImportSerializer(serializers.Serializer):
    logs = serializers.ListField(
        child=SingleManualPunchSerializer(),
        allow_empty=False,
        required=True
    )


class SinglePushPunchSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=100, required=True)
    timestamp = serializers.DateTimeField(required=True)
    event_type = serializers.CharField(max_length=20, required=False, default="UNKNOWN")
    device_log_id = serializers.CharField(max_length=255, required=False, default=None)


class PushWebhookSerializer(serializers.Serializer):
    punches = serializers.ListField(
        child=SinglePushPunchSerializer(),
        allow_empty=False,
        required=True
    )