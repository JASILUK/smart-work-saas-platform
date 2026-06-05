from channels.db import database_sync_to_async

from django.utils import timezone

from apps.chat.models import (
    Conversation,
    Message,
    MessageStatus,
    ConversationParticipant,
)

from apps.chat.services.message_service import (
    MessageService,
)


class ChatRealtimeHandler:

    def __init__(
        self,
        *,
        consumer,
    ):

        self.consumer = consumer

    # =====================================================
    # MAIN EVENT ROUTER
    # =====================================================

    async def handle(
        self,
        data,
    ):

        event_type = data.get("type")

        if event_type == "message_received":

            await self.handle_message_received(
                data=data,
            )

        elif event_type == "mark_read":

            await self.handle_mark_read(
                data=data,
            )

        elif event_type == "typing_start":

            await self.handle_typing(
                data=data,
                is_typing=True,
            )

        elif event_type == "typing_stop":

            await self.handle_typing(
                data=data,
                is_typing=False,
            )

    # =====================================================
    # MESSAGE RECEIVED ACK
    # =====================================================

    async def handle_message_received(
        self,
        *,
        data,
    ):

        message_id = data.get("message_id")

        if not message_id:
            return

        now = timezone.now()

        updated = await database_sync_to_async(
            MessageStatus.objects.filter(
                message_id=message_id,
                membership_id=self.consumer.membership_id,
                status=MessageStatus.Status.SENT,
            ).update
        )(
            status=MessageStatus.Status.DELIVERED,
            delivered_at=now,
        )

        if not updated:
            return

        message = await database_sync_to_async(
            Message.objects.prefetch_related(
                "statuses"
            ).get
        )(
            id=message_id,
        )

        await database_sync_to_async(
            MessageService.broadcast_status_update
        )(
            message,
        )

    # =====================================================
    # MARK ROOM READ
    # =====================================================

    async def handle_mark_read(
        self,
        *,
        data,
    ):

        room_id = data.get("room_id")

        if not room_id:
            return

        await self.mark_room_messages_as_read(
            room_id=room_id,
        )

    # =====================================================
    # INTERNAL READ LOGIC
    # =====================================================

    async def mark_room_messages_as_read(
        self,
        *,
        room_id,
    ):

        now = timezone.now()

        statuses = await database_sync_to_async(list)(
            MessageStatus.objects.select_related(
                "message",
                "message__conversation",
            ).filter(
                message__conversation_id=room_id,
                membership_id=self.consumer.membership_id,
                status__in=[
                    MessageStatus.Status.SENT,
                    MessageStatus.Status.DELIVERED,
                ],
            )
        )

        if not statuses:
            return

        await database_sync_to_async(
            MessageStatus.objects.filter(
                id__in=[s.id for s in statuses]
            ).update
        )(
            status=MessageStatus.Status.READ,
            delivered_at=now,
            read_at=now,
        )

        await database_sync_to_async(
            ConversationParticipant.objects.filter(
                conversation_id=room_id,
                membership_id=self.consumer.membership_id,
            ).update
        )(
            unread_count=0,
        )

        conversation = await database_sync_to_async(
            Conversation.objects.select_related(
                "last_message"
            ).get
        )(
            id=room_id,
        )

        last_message_preview = ""

        last_message = conversation.last_message

        if last_message:

            if last_message.deleted:

                last_message_preview = (
                    "This message was deleted"
                )

            elif last_message.message_type == "text":

                last_message_preview = (
                    last_message.content or ""
                )

            elif last_message.message_type == "image":

                last_message_preview = "📷 Photo"

            elif last_message.message_type == "video":

                last_message_preview = "🎥 Video"

            elif last_message.message_type == "audio":

                last_message_preview = "🎧 Audio"

            else:

                last_message_preview = (
                    last_message.file_name
                    or
                    "📎 File"
                )

        await self.consumer.channel_layer.group_send(
            (
                f"tenant_"
                f"{self.consumer.tenant_id}"
                f"_user_"
                f"{self.consumer.membership_id}"
            ),
            {
                "type": "sidebar_update",

                "conversation_id": str(room_id),

                "last_message": last_message_preview,

                "updated_at": (
                    conversation.updated_at.isoformat()
                ),

                "unread_count": 0,
            }
        )

        processed_messages = set()

        for status in statuses:

            message = status.message

            if message.id in processed_messages:
                continue

            processed_messages.add(
                message.id
            )

            refreshed_message = await database_sync_to_async(
                Message.objects.prefetch_related(
                    "statuses"
                ).get
            )(
                id=message.id,
            )

            await database_sync_to_async(
                MessageService.broadcast_status_update
            )(
                refreshed_message,
            )

    # =====================================================
    # DELIVERY SYNC ON CONNECT
    # =====================================================

    async def mark_all_as_delivered_on_connect(
        self,
    ):

        now = timezone.now()

        statuses = await database_sync_to_async(list)(
            MessageStatus.objects.select_related(
                "message"
            ).filter(
                membership_id=self.consumer.membership_id,
                status=MessageStatus.Status.SENT,
            )
        )

        if not statuses:
            return

        await database_sync_to_async(
            MessageStatus.objects.filter(
                id__in=[s.id for s in statuses]
            ).update
        )(
            status=MessageStatus.Status.DELIVERED,
            delivered_at=now,
        )

        processed_messages = set()

        for status in statuses:

            message = status.message

            if message.id in processed_messages:
                continue

            processed_messages.add(
                message.id
            )

            refreshed_message = await database_sync_to_async(
                Message.objects.prefetch_related(
                    "statuses"
                ).get
            )(
                id=message.id,
            )

            await database_sync_to_async(
                MessageService.broadcast_status_update
            )(
                refreshed_message,
            )

    # =====================================================
    # TYPING
    # =====================================================

    async def handle_typing(
        self,
        *,
        data,
        is_typing,
    ):

        room_id = data.get("room_id")

        if not room_id:
            return

        await self.consumer.channel_layer.group_send(
            (
                f"tenant_"
                f"{self.consumer.tenant_id}"
                f"_room_"
                f"{room_id}"
            ),
            {
                "type": "typing_event",
                "user_id": self.consumer.membership_id,
                "room_id": str(room_id),
                "is_typing": is_typing,
            }
        )