import logging
from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict, Any

from django.db import transaction

from apps.notifications.models import (
    Notification,
    NotificationPreference,
)
from apps.notifications.services.email_service import EmailService
from apps.notifications.services.push_service import PushService
from apps.notifications.tasks.email_tasks import send_email_task

logger = logging.getLogger(__name__)


# =========================================================
# NOTIFICATION RULE DEFINITION & REGISTRY
# =========================================================

@dataclass(frozen=True)
class NotificationRule:
    notification_type: str
    category: str
    allowed_channels: Set[str]
    preference_field: str
    supports_realtime: bool = True
    supports_push: bool = True
    supports_email: bool = False


class NotificationRuleRegistry:
    """
    Centralized registry for notification rules adhering to the Open/Closed Principle.
    New notification types can be added here without altering core pipeline execution logic.
    """
    _rules: Dict[str, NotificationRule] = {
        Notification.Type.CHAT: NotificationRule(
            notification_type=Notification.Type.CHAT,
            category="CHAT",
            allowed_channels={"IN_APP", "PUSH"},
            preference_field="chat_message_enabled",
            supports_realtime=True,
            supports_push=True,
            supports_email=False,
        ),
        Notification.Type.MEETING: NotificationRule(
            notification_type=Notification.Type.MEETING,
            category="MEETING",
            allowed_channels={"IN_APP", "PUSH", "EMAIL"},
            preference_field="meeting_enabled",
            supports_realtime=True,
            supports_push=True,
            supports_email=True,
        ),
        Notification.Type.SYSTEM: NotificationRule(
            notification_type=Notification.Type.SYSTEM,
            category="SYSTEM",
            allowed_channels={"IN_APP", "PUSH", "EMAIL"},
            preference_field="system_enabled",
            supports_realtime=True,
            supports_push=True,
            supports_email=True,
        ),
        # Future extensibility hooks ready for registration:
        # "TASK_ASSIGNED": NotificationRule(...)
        # "PAYROLL_PROCESSED": NotificationRule(...)
    }

    @classmethod
    def get_rule(cls, notification_type: str) -> NotificationRule:
        rule = cls._rules.get(notification_type)
        if not rule:
            # Default fallback for unconfigured extensions to avoid hard runtime crashes
            logger.warning("No specific notification rule found for type=%s. Falling back to default system rule.", notification_type)
            return NotificationRule(
                notification_type=notification_type,
                category="DEFAULT",
                allowed_channels={"IN_APP", "PUSH"},
                preference_field="system_enabled",
                supports_realtime=True,
                supports_push=True,
                supports_email=False,
            )
        return rule

    @classmethod
    def register_rule(cls, rule: NotificationRule) -> None:
        cls._rules[rule.notification_type] = rule


# =========================================================
# CENTRALIZED NOTIFICATION ENGINE (SERVICE LAYER)
# =========================================================

class NotificationService:

    # =====================================================
    # SINGLE SOURCE OF TRUTH: NOTIFICATION PIPELINE
    # =====================================================

    @staticmethod
    def notify(
        *,
        membership,
        notification_type: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        extra_channels: Optional[Set[str]] = None,
    ) -> Notification:
        """
        Generic, enterprise-grade notification pipeline.
        Handles rule lookup, database creation, preference validation, and channel dispatch.
        """
        data = data or {}
        rule = NotificationRuleRegistry.get_rule(notification_type)

        logger.info(
            "NOTIFICATION ENGINE START: membership=%s type=%s category=%s",
            membership.id,
            notification_type,
            rule.category,
        )

        # Step 1 & 2: Create database notification record atomically
        notification = NotificationService.create_notification(
            membership=membership,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data,
        )

        # Step 3 & 4: Fetch user preferences and evaluate allowed channels
        preferences = NotificationService._get_preferences(membership=membership)
        final_channels = NotificationService._resolve_channels(
            rule=rule,
            preferences=preferences,
            extra_channels=extra_channels,
        )

        logger.info(
            "RESOLVED CHANNELS FOR notification=%s channels=%s",
            notification.id,
            final_channels,
        )

        # Step 5: Broadcast Realtime Notification (In-App WebSockets)
        if "IN_APP" in final_channels and rule.supports_realtime:
            NotificationService._dispatch_realtime(
                membership=membership,
                notification=notification,
                data=data,
            )

        # Step 6: Queue Push Notification
        if "PUSH" in final_channels and rule.supports_push:
            NotificationService._dispatch_push(
                membership=membership,
                notification=notification,
                data=data,
            )

        # Step 7: Queue Email Delivery
        if "EMAIL" in final_channels and rule.supports_email:
            NotificationService._dispatch_email(
                membership=membership,
                title=title,
                body=body,
            )

        # Step 8: Extensibility hooks for future channels (SMS, Webhook, Slack, Teams) can plug in here seamlessly.
        NotificationService._dispatch_future_channels(
            final_channels=final_channels,
            membership=membership,
            notification=notification,
            title=title,
            body=body,
            data=data,
        )

        return notification

    # =====================================================
    # CREATE NOTIFICATION RECORD
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
    ) -> Notification:
        notification = Notification.objects.create(
            membership=membership,
            type=notification_type,
            title=title,
            body=body,
            data=data or {},
        )
        return notification

    # =====================================================
    # BACKWARD COMPATIBLE PUBLIC WRAPPERS
    # =====================================================

    @staticmethod
    def send_chat_notification(
        *,
        membership,
        sender_membership,
        conversation,
        message,
    ) -> Notification:
        logger.warning(
            "CHAT NOTIFICATION START membership=%s conversation=%s message=%s",
            membership.id,
            conversation.id,
            message.id,
        )

        preview = NotificationService._build_message_preview(message)
        title = (
            sender_membership.user.get_full_name()
            or sender_membership.user.username
        )

        logger.warning("CHAT NOTIFICATION PREVIEW=%s", preview)

        data = {
            "conversation_id": str(conversation.id),
            "message_id": str(message.id),
            "sender_membership_id": str(sender_membership.id),
            "room_id": str(conversation.id),  # Preserved for push compatibility
        }

        # Delegate execution into the unified notification engine pipeline
        return NotificationService.notify(
            membership=membership,
            notification_type=Notification.Type.CHAT,
            title=title,
            body=preview,
            data=data,
        )

    @staticmethod
    def send_system_notification(
        *,
        membership,
        title,
        body,
        data=None,
    ) -> Notification:
        return NotificationService.notify(
            membership=membership,
            notification_type=Notification.Type.SYSTEM,
            title=title,
            body=body,
            data=data,
        )

    @staticmethod
    def send_meeting_notification(
        *,
        membership,
        title,
        body,
        data=None,
    ) -> Notification:
        return NotificationService.notify(
            membership=membership,
            notification_type=Notification.Type.MEETING,
            title=title,
            body=body,
            data=data,
        )

    # =====================================================
    # PRIVATE DISPATCH & RESOLUTION HELPERS
    # =====================================================

    @staticmethod
    def _resolve_channels(
        *,
        rule: NotificationRule,
        preferences: NotificationPreference,
        extra_channels: Optional[Set[str]] = None,
    ) -> Set[str]:
        """
        Intersects rule-allowed channels with global/category preference flags.
        """
        # Master push switch check
        if not getattr(preferences, "push_enabled", True):
            active_channels = rule.allowed_channels - {"PUSH"}
        else:
            active_channels = set(rule.allowed_channels)

        # Specific category preference flag check (e.g., chat_message_enabled, meeting_enabled, system_enabled)
        pref_field = rule.preference_field
        if pref_field and hasattr(preferences, pref_field):
            if not getattr(preferences, pref_field):
                # If specific category preference is disabled, remove PUSH and EMAIL, keep IN_APP database logging
                active_channels = active_channels.intersection({"IN_APP"})

        # Category email flag check
        if "EMAIL" in active_channels and not getattr(preferences, "email_enabled", True):
            active_channels.remove("EMAIL")

        if extra_channels:
            active_channels.update(extra_channels)

        return active_channels

    @staticmethod
    def _dispatch_realtime(*, membership, notification, data):
        try:
            PushService.broadcast_in_app_notification(
                membership=membership,
                notification=notification,
            )
        except Exception as e:
            logger.error("Failed to dispatch realtime notification: %s", str(e), exc_info=True)

    @staticmethod
    def _dispatch_push(*, membership, notification, data):
        try:
            room_id = data.get("room_id") or data.get("conversation_id")
            if room_id:
                PushService.send_push_notification(
                    membership=membership,
                    notification=notification,
                    room_id=room_id,
                )
            else:
                PushService.send_push_notification(
                    membership=membership,
                    notification=notification,
                )
        except Exception as e:
            logger.error("Failed to dispatch push notification: %s", str(e), exc_info=True)

    @staticmethod
    def _dispatch_email(*, membership, title, body):
        email = getattr(membership.user, "email", None)
        if not email:
            return

        transaction.on_commit(
            lambda: send_email_task.delay(
                recipient=email,
                subject=title,
                content=body,
            )
        )

    @staticmethod
    def _dispatch_future_channels(*, final_channels, membership, notification, title, body, data):
        """
        Extension point for SMS, Webhooks, Slack, and Teams integration.
        Architecturally prepared for zero-friction scaling.
        """
        if "SMS" in final_channels:
            # TODO: Integrate SMS Service Gateway
            pass
        if "WEBHOOK" in final_channels:
            # TODO: Integrate Webhook Dispatcher
            pass
        if "SLACK" in final_channels:
            # TODO: Integrate Slack App API
            pass
        if "TEAMS" in final_channels:
            # TODO: Integrate Microsoft Teams Connector API
            pass

    @staticmethod
    def _get_preferences(*, membership) -> NotificationPreference:
        preferences, _ = NotificationPreference.objects.get_or_create(
            membership=membership,
        )
        return preferences

    @staticmethod
    def _build_message_preview(message) -> str:
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
            return message.file_name or "📎 File"

        return "New message"