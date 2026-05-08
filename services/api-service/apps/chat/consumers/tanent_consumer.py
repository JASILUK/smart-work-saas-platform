from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from django.utils import timezone
from django.conf import settings

from asgiref.sync import sync_to_async

from apps.chat.models import (
    Conversation,
    Message,
    MessageStatus,
    ConversationParticipant,
)

from apps.chat.services.message_service import MessageService
from apps.companies.models import Membership

import redis
import json


redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


class TenantConsumer(AsyncWebsocketConsumer):

    # =========================================================
    # CONNECT
    # =========================================================
    async def connect(self):

        try:

            user = self.scope.get("user")
            tenant_id = self.scope.get("tenant_id")
            membership = self.scope.get("membership")

            if (
                not user
                or user.is_anonymous
                or not tenant_id
                or not membership
            ):
                await self.close()
                return

            self.user = user
            self.tenant_id = tenant_id
            self.membership_id = membership.id
            self.socket_id = self.channel_name

            self.user_group = (
                f"tenant_{tenant_id}_user_{self.membership_id}"
            )

            self.tenant_group = (
                f"tenant_{tenant_id}"
            )

            self.connection_key = (
                f"user:{self.membership_id}:connections"
            )

            self.online_set = (
                f"online_users:{self.tenant_id}"
            )

            # join groups
            await self.channel_layer.group_add(
                self.user_group,
                self.channel_name,
            )

            await self.channel_layer.group_add(
                self.tenant_group,
                self.channel_name,
            )

            await self.accept()

            # track socket
            await sync_to_async(redis_client.sadd)(
                self.connection_key,
                self.socket_id,
            )

            count = await sync_to_async(redis_client.scard)(
                self.connection_key
            )

            print(
                f"✅ WS CONNECTED user={self.membership_id}, count={count}"
            )

            # first connection => online
            if count == 1:

                await sync_to_async(redis_client.sadd)(
                    self.online_set,
                    self.membership_id,
                )

                await self.channel_layer.group_send(
                    self.tenant_group,
                    {
                        "type": "presence_update",
                        "user_id": self.membership_id,
                        "status": "online",
                    }
                )

            # snapshot
            online_users = await sync_to_async(
                redis_client.smembers
            )(self.online_set)

            await self.send(
                text_data=json.dumps({
                    "type": "presence_snapshot",
                    "users": list(map(int, online_users)),
                })
            )

            # auto delivery sync
            await self.mark_all_as_delivered_on_connect()

        except Exception as e:
            print("❌ CONNECT ERROR:", str(e))
            await self.close()

    # =========================================================
    # DISCONNECT
    # =========================================================
    async def disconnect(self, close_code):

        try:

            if hasattr(self, "user_group"):
                await self.channel_layer.group_discard(
                    self.user_group,
                    self.channel_name,
                )

            if hasattr(self, "tenant_group"):
                await self.channel_layer.group_discard(
                    self.tenant_group,
                    self.channel_name,
                )

            if hasattr(self, "connection_key"):

                await sync_to_async(redis_client.srem)(
                    self.connection_key,
                    self.socket_id,
                )

                count = await sync_to_async(redis_client.scard)(
                    self.connection_key
                )

                print(
                    f"❌ WS DISCONNECT user={self.membership_id}, count={count}"
                )

                if count == 0:

                    now = timezone.now()

                    # remove online
                    await sync_to_async(redis_client.srem)(
                        self.online_set,
                        self.membership_id,
                    )

                    # last seen redis
                    await sync_to_async(redis_client.set)(
                        f"user:{self.membership_id}:last_seen",
                        now.isoformat(),
                    )

                    # last seen db
                    await database_sync_to_async(
                        Membership.objects.filter(
                            id=self.membership_id
                        ).update
                    )(
                        last_seen=now
                    )

                    # broadcast offline
                    await self.channel_layer.group_send(
                        self.tenant_group,
                        {
                            "type": "presence_update",
                            "user_id": self.membership_id,
                            "status": "offline",
                        }
                    )

                    await self.channel_layer.group_send(
                        self.tenant_group,
                        {
                            "type": "last_seen_update",
                            "user_id": self.membership_id,
                            "last_seen": now.isoformat(),
                        }
                    )

        except Exception as e:
            print("❌ DISCONNECT ERROR:", str(e))

    # =========================================================
    # RECEIVE
    # =========================================================
    async def receive(self, text_data):

        try:

            data = json.loads(text_data)
            event_type = data.get("type")

            if event_type == "join_room":
                await self.join_room(data)

            elif event_type == "leave_room":
                await self.leave_room(data)

            elif event_type == "message_received":
                await self.handle_message_received(data)

            elif event_type == "mark_read":
                await self.handle_mark_read(data)

            elif event_type == "typing_start":
                await self.handle_typing(data, True)

            elif event_type == "typing_stop":
                await self.handle_typing(data, False)

        except Exception as e:
            print("❌ RECEIVE ERROR:", str(e))

    # =========================================================
    # JOIN ROOM
    # =========================================================
    async def join_room(self, data):

        room_id = data.get("room_id")

        if not room_id:
            return

        room_group = (
            f"tenant_{self.tenant_id}_room_{room_id}"
        )

        await self.channel_layer.group_add(
            room_group,
            self.channel_name,
        )

        # mark active room
        await sync_to_async(redis_client.sadd)(
            f"room:{self.tenant_id}:{room_id}",
            self.membership_id,
        )

        # auto read
        await self.mark_room_messages_as_read(room_id)

    # =========================================================
    # LEAVE ROOM
    # =========================================================
    async def leave_room(self, data):

        room_id = data.get("room_id")

        if not room_id:
            return

        await self.channel_layer.group_discard(
            f"tenant_{self.tenant_id}_room_{room_id}",
            self.channel_name,
        )

        await sync_to_async(redis_client.srem)(
            f"room:{self.tenant_id}:{room_id}",
            self.membership_id,
        )

    # =========================================================
    # MESSAGE RECEIVED ACK
    # =========================================================
    async def handle_message_received(self, data):

        message_id = data.get("message_id")

        if not message_id:
            return

        now = timezone.now()

        updated = await database_sync_to_async(
            MessageStatus.objects.filter(
                message_id=message_id,
                membership_id=self.membership_id,
                status=MessageStatus.Status.SENT,
            ).update
        )(
            status=MessageStatus.Status.DELIVERED,
            delivered_at=now,
        )

        if not updated:
            return

        message = await database_sync_to_async(
            Message.objects.prefetch_related("statuses").get
        )(id=message_id)

        await database_sync_to_async(
            MessageService.broadcast_status_update
        )(message)

    # =========================================================
    # MARK ROOM READ
    # =========================================================
    async def handle_mark_read(self, data):

        room_id = data.get("room_id")

        if not room_id:
            return

        await self.mark_room_messages_as_read(room_id)

    # =========================================================
    # INTERNAL READ LOGIC
    # =========================================================
    async def mark_room_messages_as_read(self, room_id):

        now = timezone.now()

        # =====================================================
        # GET TARGET STATUSES
        # =====================================================
        statuses = await database_sync_to_async(list)(
            MessageStatus.objects.select_related(
                "message",
                "message__conversation",
            ).filter(
                message__conversation_id=room_id,
                membership_id=self.membership_id,
                status__in=[
                    MessageStatus.Status.SENT,
                    MessageStatus.Status.DELIVERED,
                ]
            )
        )

        if not statuses:
            return

        # =====================================================
        # UPDATE STATUS -> READ
        # =====================================================
        await database_sync_to_async(
            MessageStatus.objects.filter(
                id__in=[s.id for s in statuses]
            ).update
        )(
            status=MessageStatus.Status.READ,
            delivered_at=now,
            read_at=now,
        )

        # =====================================================
        # RESET UNREAD COUNT
        # =====================================================
        await database_sync_to_async(
            ConversationParticipant.objects.filter(
                conversation_id=room_id,
                membership_id=self.membership_id,
            ).update
        )(
            unread_count=0
        )

        # =====================================================
        # GET UPDATED CONVERSATION
        # =====================================================
        conversation = await database_sync_to_async(
            Conversation.objects.select_related(
                "last_message"
            ).get
        )(
            id=room_id
        )

        # =====================================================
        # LAST MESSAGE PREVIEW
        # =====================================================
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
                    last_message.file_name or "📎 File"
                )

        # =====================================================
        # SIDEBAR REALTIME RESET
        # =====================================================
        await self.channel_layer.group_send(
            f"tenant_{self.tenant_id}_user_{self.membership_id}",
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

        # =====================================================
        # BROADCAST STATUS UPDATES
        # =====================================================
        processed_messages = set()

        for status in statuses:

            message = status.message

            if message.id in processed_messages:
                continue

            processed_messages.add(message.id)

            refreshed_message = await database_sync_to_async(
                Message.objects.prefetch_related(
                    "statuses"
                ).get
            )(
                id=message.id
            )

            await database_sync_to_async(
                MessageService.broadcast_status_update
            )(
                refreshed_message
            )

    # =========================================================
    # CONNECT DELIVERY SYNC
    # =========================================================
    async def mark_all_as_delivered_on_connect(self):

        now = timezone.now()

        statuses = await database_sync_to_async(list)(
            MessageStatus.objects.select_related(
                "message"
            ).filter(
                membership_id=self.membership_id,
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

            processed_messages.add(message.id)

            message = await database_sync_to_async(
                Message.objects.prefetch_related(
                    "statuses"
                ).get
            )(id=message.id)

            await database_sync_to_async(
                MessageService.broadcast_status_update
            )(message)

    # =========================================================
    # TYPING
    # =========================================================
    async def handle_typing(self, data, is_typing):

        room_id = data.get("room_id")

        if not room_id:
            return

        await self.channel_layer.group_send(
            f"tenant_{self.tenant_id}_room_{room_id}",
            {
                "type": "typing_event",
                "user_id": self.membership_id,
                "room_id": str(room_id),
                "is_typing": is_typing,
            }
        )

    # =========================================================
    # EVENTS
    # =========================================================
    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    async def incoming_message(self, event):
        await self.send(text_data=json.dumps(event))

    async def sidebar_update(self, event):
        await self.send(text_data=json.dumps(event))

    async def status_update(self, event):
        await self.send(text_data=json.dumps(event))

    async def presence_update(self, event):
        await self.send(text_data=json.dumps(event))

    async def typing_event(self, event):
        await self.send(text_data=json.dumps(event))

    async def last_seen_update(self, event):
        await self.send(text_data=json.dumps(event))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps(event))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps(event))

    async def conversation_created(self, event):
        await self.send(
            text_data=json.dumps(event)
        )