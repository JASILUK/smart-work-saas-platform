from asgiref.sync import async_to_sync

from channels.layers import get_channel_layer

from django.conf import settings
from django.db import transaction
import redis

from apps.notifications.models import (
    NotificationDevice,
)
from apps.notifications.tasks.push_tasks import (
    send_push_notification_task,
)
import logging

logger = logging.getLogger(__name__)


redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


class PushService:

    # =====================================================
    # MAIN PUSH ENTRY
    # =====================================================

    @staticmethod
    def send_push_notification(
        *,
        membership,
        notification,
        room_id=None,
    ):

        logger.info(
            "[PUSH] Start membership=%s notification=%s room_id=%s",
            membership.id,
            notification.id,
            room_id,
        )

        allowed = PushService.should_send_push(
            membership=membership,
            room_id=room_id,
        )

        logger.info(
            "[PUSH] Eligibility result=%s membership=%s",
            allowed,
            membership.id,
        )

        if not allowed:

            logger.warning(
                "[PUSH] Blocked by eligibility membership=%s",
                membership.id,
            )

            return

        devices = (
            NotificationDevice.objects
            .filter(
                membership=membership,
                is_active=True,
            )
            .only(
                "id",
                "token",
                "platform",
            )
        )

        device_count = devices.count()

        logger.info(
            "[PUSH] Active devices=%s membership=%s",
            device_count,
            membership.id,
        )

        if device_count == 0:

            logger.warning(
                "[PUSH] No active devices membership=%s",
                membership.id,
            )

            return

        for device in devices:

            current_device_id = str(device.id)
            current_notification_id = str(notification.id)

            transaction.on_commit(
                lambda d=current_device_id,
                    n=current_notification_id:
                send_push_notification_task.delay(
                    device_id=d,
                    notification_id=n,
                )
            )   

    # =====================================================
    # PUSH ELIGIBILITY
    # =====================================================

    @staticmethod
    def should_send_push(
        *,
        membership,
        room_id=None,
    ):

        # ================================================
        # ONLINE USER CHECK
        # ================================================

        online_key = (
            f"online_users:{membership.company_id}"
        )

        is_online = bool(
            redis_client.sismember(
                online_key,
                str(membership.id),
            )
        )

        logger.info(
            "[PUSH] Online check membership=%s online=%s",
            membership.id,
            is_online,
        )

        # ================================================
        # OFFLINE USER
        # ================================================

        if not is_online:
            return True

        # ================================================
        # NO ROOM CONTEXT
        # ================================================

        if not room_id:
            return True

        # ================================================
        # ACTIVE ROOM CHECK
        # ================================================

        room_key = (
            f"room:{membership.company_id}:{room_id}"
        )

        inside_room = bool(
            redis_client.sismember(
                room_key,
                str(membership.id),
            )
        )

        logger.info(
            "[PUSH] Room check room=%s inside=%s",
            room_id,
            inside_room,
        )

        # ================================================
        # USER ALREADY INSIDE CHAT ROOM
        # ================================================

        if inside_room:
            return False

        return True

    # =====================================================
    # IN-APP REALTIME NOTIFICATION
    # =====================================================

    @staticmethod
    def broadcast_in_app_notification(
        *,
        membership_id,
        payload,
    ):

        channel_layer = get_channel_layer()

        async_to_sync(
            channel_layer.group_send
        )(
            f"tenant_user_{membership_id}",
            {
                "type": "notification_event",
                "data": payload,
            },
        )



