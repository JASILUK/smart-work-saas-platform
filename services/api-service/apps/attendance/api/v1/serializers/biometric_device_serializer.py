from rest_framework import serializers
from apps.attendance.models.biometric_device import BiometricDevice


class BiometricDeviceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = BiometricDevice
        fields = ["id", "name", "device_code", "brand", "model_name", "sync_mode", "is_active", "last_synced_at"]
        read_only_fields = fields


class BiometricDeviceDetailSerializer(serializers.ModelSerializer):
    mapping_count = serializers.SerializerMethodField()

    class Meta:
        model = BiometricDevice
        fields = [
            "id", "name", "device_code", "brand", "model_name", "ip_address", 
            "port", "serial_number", "timezone", "sync_mode", "is_active", 
            "last_synced_at", "mapping_count", "created_at", "updated_at"
        ]
        read_only_fields = fields

    def get_mapping_count(self, obj: BiometricDevice) -> int:
        return obj.employee_mappings.count()


class BiometricDeviceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BiometricDevice
        fields = ["name", "device_code", "brand", "model_name", "ip_address", "port", "serial_number", "timezone", "sync_mode", "is_active"]


class BiometricDeviceUpdateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)
    device_code = serializers.CharField(required=False)
    sync_mode = serializers.CharField(required=False)

    class Meta:
        model = BiometricDevice
        fields = ["name", "device_code", "brand", "model_name", "ip_address", "port", "serial_number", "timezone", "sync_mode", "is_active"]