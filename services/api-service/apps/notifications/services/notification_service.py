from django.db import transaction

from apps.notifications.models import (
    Notification,
    NotificationPreference,
)

from apps.notifications.services.email_service import EmailService
from apps.notifications.services.push_service import (
    PushService,
)
from django.db import transaction

from apps.notifications.tasks.email_tasks import (
    send_email_task,    
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

        import logging

        logger = logging.getLogger(__name__)

        logger.warning(
            "CHAT NOTIFICATION START membership=%s conversation=%s message=%s",
            membership.id,
            conversation.id,
            message.id,
        )

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

        logger.warning(
            "CHAT NOTIFICATION PREVIEW=%s",
            preview,
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

        logger.warning(
            "CHAT NOTIFICATION CREATED notification=%s",
            notification.id,
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

        logger.warning(
            "PREFERENCES push=%s chat=%s",
            preferences.push_enabled,
            preferences.chat_message_enabled,
        )

        if not preferences.push_enabled:

            logger.warning(
                "PUSH BLOCKED BY push_enabled=False"
            )

            return notification

        if not preferences.chat_message_enabled:

            logger.warning(
                "PUSH BLOCKED BY chat_message_enabled=False"
            )

            return notification

        logger.warning(
            "CALLING PUSH SERVICE"
        )

        # ================================================
        # PUSH DELIVERY
        # ================================================

        PushService.send_push_notification(
            membership=membership,
            notification=notification,
            room_id=conversation.id,
        )

        logger.warning(
            "PUSH SERVICE FINISHED"
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

        if not preferences.system_enabled:
            return notification

        if preferences.push_enabled:

            PushService.send_push_notification(
                membership=membership,
                notification=notification,
            )

        NotificationService._send_email_if_enabled(
            membership=membership,
            preferences=preferences,
            title=title,
            body=body,
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

        if not preferences.meeting_enabled:
            return notification

        if preferences.push_enabled:

            PushService.send_push_notification(
                membership=membership,
                notification=notification,
            )

        NotificationService._send_email_if_enabled(
            membership=membership,
            preferences=preferences,
            title=title,
            body=body,
        )

        return notification
    


    # =====================================================
    # EMAIL DELIVERY
    # =====================================================

    @staticmethod
    def _send_email_if_enabled(
        *,
        membership,
        preferences,
        title,
        body,
    ):

        if not preferences.email_enabled:
            return

        email = getattr(
            membership.user,
            "email",
            None,
        )

        if not email:
            return

        

        transaction.on_commit(
            lambda: send_email_task.delay(
                recipient=email,
                subject=title,
                content=body,
            )
        )

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