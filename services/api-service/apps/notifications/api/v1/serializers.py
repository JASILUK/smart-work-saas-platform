from rest_framework import serializers

from apps.notifications.models import (
    NotificationDevice,
    NotificationPreference,
)


class RegisterDeviceSerializer(
    serializers.Serializer
):

    device_id = serializers.CharField(
        max_length=255,
    )

    token = serializers.CharField()

    platform = serializers.ChoiceField(
        choices=NotificationDevice.Platform.choices
    )

    device_name = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class DeactivateDeviceSerializer(
    serializers.Serializer
):

    device_id = serializers.CharField(
        max_length=255,
    )


class NotificationPreferenceSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = NotificationPreference

        fields = [
            "push_enabled",
            "sound_enabled",
            "chat_message_enabled",
            "mention_enabled",
            "meeting_enabled",
            "attendance_enabled",
            "system_enabled",
        ]

class NotificationDeviceSerializer(
    serializers.ModelSerializer
):

    class Meta:

        model = NotificationDevice

        fields = [
            "id",
            "device_id",
            "platform",
            "device_name",
            "is_active",
            "created_at",
            "updated_at",
        ]