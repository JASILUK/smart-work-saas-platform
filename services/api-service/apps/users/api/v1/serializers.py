from rest_framework import serializers

from apps.users.models import MFADevice


class RegisterInputSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    username = serializers.CharField(max_length=30)


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField(max_length=6, min_length=6)


class ResendVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()


class StandardLoginSerializer(serializers.Serializer):
    """Validates standard email and password login."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class RegisterWithCompanySerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    username = serializers.CharField(max_length=150)
    company_name = serializers.CharField(max_length=255)

    def validate_company_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Company name too short.")
        return value.strip()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class MFAVerifySerializer(serializers.Serializer):

    device_id = serializers.IntegerField()

    code = serializers.CharField(max_length=6)


class MFADeviceListSerializer(serializers.ModelSerializer):

    class Meta:
        model = MFADevice
        fields = ["id", "name", "is_active", "created_at"]


class MFASetupSerializer(serializers.Serializer):

    device_name = serializers.CharField(max_length=100)
