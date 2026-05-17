from django.db import transaction

from apps.notifications.models import (
    Notification,
    NotificationPreference,
)

from apps.notifications.services.push_service import (
    PushService,
)


class NotificationService:

    # =====================================================
    # CREATE NOTIFICATION
    # =====================================================

    @staticmethod
    @transaction.atomic
    def create_notification(
        *,
        membership,
        notification_type,
        title,
        body,
        data=None,
    ):

        notification = Notification.objects.create(
            membership=membership,
            type=notification_type,
            title=title,
            body=body,
            data=data or {},
        )

        return notification

    # =====================================================
    # CHAT MESSAGE NOTIFICATION
    # =====================================================

    @staticmethod
    def send_chat_notification(
        *,
        membership,
        sender_membership,
        conversation,
        message,
    ):

        # ================================================
        # MESSAGE PREVIEW
        # ================================================

        preview = (
            NotificationService
            ._build_message_preview(message)
        )

        title = (
            sender_membership.user.get_full_name()
            or sender_membership.user.username
        )

        # ================================================
        # DATABASE NOTIFICATION
        # ================================================

        notification = (
            NotificationService.create_notification(
                membership=membership,
                notification_type=Notification.Type.CHAT,
                title=title,
                body=preview,
                data={
                    "conversation_id": str(
                        conversation.id
                    ),
                    "message_id": str(
                        message.id
                    ),
                    "sender_membership_id": str(
                        sender_membership.id
                    ),
                },
            )
        )

        # ================================================
        # USER PREFERENCES
        # ================================================

        preferences = (
            NotificationService
            ._get_preferences(
                membership=membership,
            )
        )

        if not preferences.push_enabled:
            return notification

        if not preferences.chat_message_enabled:
            return notification

        # ================================================
        # PUSH DELIVERY
        # ================================================

        PushService.send_push_notification(
            membership=membership,
            notification=notification,
            room_id=conversation.id,
        )

        return notification

    # =====================================================
    # SYSTEM NOTIFICATION
    # =====================================================

    @staticmethod
    def send_system_notification(
        *,
        membership,
        title,
        body,
        data=None,
    ):

        notification = (
            NotificationService.create_notification(
                membership=membership,
                notification_type=Notification.Type.SYSTEM,
                title=title,
                body=body,
                data=data or {},
            )
        )

        preferences = (
            NotificationService
            ._get_preferences(
                membership=membership,
            )
        )

        if not preferences.push_enabled:
            return notification

        if not preferences.system_enabled:
            return notification

        PushService.send_push_notification(
            membership=membership,
            notification=notification,
        )

        return notification

    # =====================================================
    # MEETING NOTIFICATION
    # =====================================================

    @staticmethod
    def send_meeting_notification(
        *,
        membership,
        title,
        body,
        data=None,
    ):

        notification = (
            NotificationService.create_notification(
                membership=membership,
                notification_type=Notification.Type.MEETING,
                title=title,
                body=body,
                data=data or {},
            )
        )

        preferences = (
            NotificationService
            ._get_preferences(
                membership=membership,
            )
        )

        if not preferences.push_enabled:
            return notification

        if not preferences.meeting_enabled:
            return notification

        PushService.send_push_notification(
            membership=membership,
            notification=notification,
        )

        return notification

    # =====================================================
    # GET OR CREATE PREFERENCES
    # =====================================================

    @staticmethod
    def _get_preferences(
        *,
        membership,
    ):

        preferences, _ = (
            NotificationPreference.objects
            .get_or_create(
                membership=membership,
            )
        )

        return preferences

    # =====================================================
    # MESSAGE PREVIEW BUILDER
    # =====================================================

    @staticmethod
    def _build_message_preview(message):

        if message.deleted:
            return "This message was deleted"

        if message.message_type == "text":

            return (
                message.content[:120]
                if message.content
                else "New message"
            )

        if message.message_type == "image":
            return "📷 Photo"

        if message.message_type == "video":
            return "🎥 Video"

        if message.message_type == "audio":
            return "🎧 Audio"

        if message.message_type == "file":

            return (
                message.file_name
                or "📎 File"
            )

        return "New message"