

import json
import uuid

from django.conf import settings

from django.utils import timezone

from asgiref.sync import sync_to_async

import redis


# =====================================================
# REDIS
# =====================================================

redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


# =====================================================
# REALTIME CHAT HANDLER
# =====================================================

class MeetingChatRealtimeHandler:

    # =================================================
    # INIT
    # =================================================

    def __init__(
        self,
        *,
        consumer,
    ):

        self.consumer = consumer

    # =================================================
    # MAIN ROUTER
    # =================================================

    async def handle(
        self,
        data,
    ):

        event_type = data.get(
            "type"
        )

        # =============================================
        # SEND MESSAGE
        # =============================================

        if (
            event_type
            ==
            "meeting_message"
        ):

            await self.send_message(
                data=data,
            )

        # =============================================
        # TYPING
        # =============================================

        elif (
            event_type
            ==
            "meeting_typing"
        ):

            await self.typing_event(
                data=data,
            )

        # =============================================
        # CHAT SNAPSHOT
        # =============================================

        elif (
            event_type
            ==
            "meeting_chat_snapshot"
        ):

            await self.send_chat_snapshot(
                meeting_id=data.get(
                    "meeting_id"
                ),
            )

    # =================================================
    # SEND MESSAGE
    # =================================================

    async def send_message(
        self,
        *,
        data,
    ):

        meeting_id = data.get(
            "meeting_id"
        )

        message = (
            data.get("message") or ""
        ).strip()

        # =============================================
        # VALIDATION
        # =============================================

        if (
            not meeting_id
            or
            not message
        ):

            return

        # =============================================
        # PAYLOAD
        # =============================================

        payload = {

            "id": str(
                uuid.uuid4()
            ),

            "type": (
                "meeting_message"
            ),

            "meeting_id": str(
                meeting_id
            ),

            "message": message,

            "sender": {

                "membership_id": (
                    self.consumer.membership_id
                ),

                "username": (
                    self.consumer.username
                ),
            },

            "created_at": (
                timezone.now()
                .isoformat()
            ),
        }

        # =============================================
        # REDIS KEY
        # =============================================

        redis_key = (
            f"meeting_chat:"
            f"{meeting_id}"
        )

        # =============================================
        # STORE MESSAGE
        # =============================================

        await sync_to_async(
            redis_client.rpush
        )(
            redis_key,
            json.dumps(payload),
        )

        # =============================================
        # KEEP LAST 200
        # =============================================

        await sync_to_async(
            redis_client.ltrim
        )(
            redis_key,
            -200,
            -1,
        )

        # =============================================
        # AUTO EXPIRE
        # =============================================

        await sync_to_async(
            redis_client.expire
        )(
            redis_key,
            60 * 60 * 24,
        )

        # =============================================
        # BROADCAST
        # =============================================

        await self.consumer.channel_layer.group_send(
            (
                f"tenant_"
                f"{self.consumer.tenant_id}"
                f"_meeting_"
                f"{meeting_id}"
            ),
            payload,
        )

    # =================================================
    # TYPING EVENT
    # =================================================

    async def typing_event(
        self,
        *,
        data,
    ):

        meeting_id = data.get(
            "meeting_id"
        )

        is_typing = bool(
            data.get(
                "is_typing"
            )
        )

        if not meeting_id:
            return

        await self.consumer.channel_layer.group_send(
            (
                f"tenant_"
                f"{self.consumer.tenant_id}"
                f"_meeting_"
                f"{meeting_id}"
            ),
            {
                "type": (
                    "meeting_typing"
                ),

                "meeting_id": str(
                    meeting_id
                ),

                "user": {

                    "membership_id": (
                        self.consumer.membership_id
                    ),

                    "username": (
                        self.consumer.username
                    ),
                },

                "is_typing":
                    is_typing,
            }
        )

    # =================================================
    # CHAT SNAPSHOT
    # =================================================

    async def send_chat_snapshot(
        self,
        *,
        meeting_id,
    ):

        if not meeting_id:
            return

        # =============================================
        # REDIS KEY
        # =============================================

        redis_key = (
            f"meeting_chat:"
            f"{meeting_id}"
        )

        # =============================================
        # LOAD MESSAGES
        # =============================================

        messages = await sync_to_async(
            redis_client.lrange
        )(
            redis_key,
            0,
            -1,
        )

        # =============================================
        # NORMALIZE
        # =============================================

        payload = [

            json.loads(message)

            for message

            in messages
        ]

        # =============================================
        # SEND SNAPSHOT
        # =============================================

        await self.consumer.send(
            text_data=json.dumps(
                {
                    "type": (
                        "meeting_chat_snapshot"
                    ),

                    "meeting_id": str(
                        meeting_id
                    ),

                    "messages":
                        payload,
                }
            )
        )



