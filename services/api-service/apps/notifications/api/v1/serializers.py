from rest_framework import serializers

from apps.notifications.models import (
    Notification,
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
            "email_enabled",
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




class NotificationSerializer(serializers.ModelSerializer):
    """
    Core serializer for Notification objects, exposing only consumer-facing fields.
    """
    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "title",
            "body",
            "data",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields


class NotificationDetailSerializer(NotificationSerializer):
    """
    Detail serializer for individual notifications. Reuses NotificationSerializer fields.
    """
    pass


class NotificationUnreadCountSerializer(serializers.Serializer):
    """
    Serializer for returning unread notification count.
    """
    unread_count = serializers.IntegerField(read_only=True)


class NotificationListQuerySerializer(serializers.Serializer):
    """
    Query parameter validation serializer for the notification list endpoint.
    """
    is_read = serializers.BooleanField(required=False, allow_null=True)
    
    # 🔥 Change 'type' to 'notification_type' to match what the frontend and service expect
    notification_type = serializers.ChoiceField(
        choices=Notification.Type.choices,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    
    search = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    created_after = serializers.DateTimeField(required=False, allow_null=True)
    created_before = serializers.DateTimeField(required=False, allow_null=True)

    def validate_is_read(self, value):
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return value

class NotificationReadSerializer(serializers.Serializer):
    """
    Serializer for marking a single notification as read (request body validation if needed).
    """
    pass


class NotificationReadAllSerializer(serializers.Serializer):
    """
    Serializer for the mark all read response payload.
    """
    updated_count = serializers.IntegerField(read_only=True)


class NotificationClearReadSerializer(serializers.Serializer):
    """
    Serializer for the clear read notifications response payload.
    """
    deleted_count = serializers.IntegerField(read_only=True)