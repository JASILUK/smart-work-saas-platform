from rest_framework import serializers
from apps.attendance.models.biometric_employee_mapping import BiometricEmployeeMapping


class BiometricEmployeeMappingListSerializer(serializers.ModelSerializer):
    membership = serializers.SerializerMethodField()
    device = serializers.SerializerMethodField()

    class Meta:
        model = BiometricEmployeeMapping
        fields = ["id", "membership", "device", "device_user_id", "is_active"]
        read_only_fields = fields

    def get_membership(self, obj: BiometricEmployeeMapping) -> dict:
        return {"id": obj.membership.id, "username": obj.membership.user.username}

    def get_device(self, obj: BiometricEmployeeMapping) -> dict:
        return {"id": obj.device.id, "name": obj.device.name}


class BiometricEmployeeMappingDetailSerializer(serializers.ModelSerializer):
    employee_username = serializers.CharField(source="membership.user.username", read_only=True)
    device_name = serializers.CharField(source="device.name", read_only=True)
    creator_username = serializers.CharField(source="created_by.user.username", read_only=True, default=None)

    class Meta:
        model = BiometricEmployeeMapping
        fields = [
            "id", "membership", "employee_username", "device", "device_name", 
            "device_user_id", "is_active", "enrolled_at", "created_by", 
            "creator_username", "created_at", "updated_at"
        ]
        read_only_fields = fields


class BiometricEmployeeMappingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BiometricEmployeeMapping
        fields = ["membership", "device", "device_user_id", "is_active"]


class BiometricEmployeeMappingUpdateSerializer(serializers.ModelSerializer):
    device_user_id = serializers.CharField(required=False)

    class Meta:
        model = BiometricEmployeeMapping
        fields = ["device_user_id", "is_active"]