from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json
from django.utils import timezone
from apps.chat.models import MessageStatus, Message
from apps.companies.models import Membership
import redis
from django.conf import settings
from asgiref.sync import sync_to_async

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


class TenantConsumer(AsyncWebsocketConsumer):

    # =========================
    # CONNECT
    # =========================
    async def connect(self):
        try:
            user = self.scope.get("user")
            tenant_id = self.scope.get("tenant_id")
            membership = self.scope.get("membership")

            if not user or user.is_anonymous or not tenant_id or not membership:
                await self.close()
                return

            self.user = user
            self.tenant_id = tenant_id
            self.membership_id = membership.id
            self.socket_id = self.channel_name

            self.user_group = f"tenant_{tenant_id}_user_{self.membership_id}"
            self.tenant_group = f"tenant_{tenant_id}"

            self.connection_key = f"user:{self.membership_id}:connections"
            self.online_set = f"online_users:{self.tenant_id}"

            await self.channel_layer.group_add(self.user_group, self.channel_name)
            await self.channel_layer.group_add(self.tenant_group, self.channel_name)

            await self.accept()

            # 🔥 track connection
            await sync_to_async(redis_client.sadd)(
                self.connection_key,
                self.socket_id
            )

            count = await sync_to_async(redis_client.scard)(self.connection_key)

            print(f"✅ WS CONNECTED user={self.membership_id}, count={count}")

            # 🔥 FIRST CONNECTION = ONLINE
            if count == 1:
                await sync_to_async(redis_client.sadd)(
                    self.online_set,
                    self.membership_id
                )

                print(f"🔥 BROADCAST ONLINE {self.membership_id}")

                await self.channel_layer.group_send(
                    self.tenant_group,
                    {
                        "type": "presence_update",
                        "user_id": self.membership_id,
                        "status": "online"
                    }
                )

            # 🔥 SEND SNAPSHOT (CRITICAL)
            online_users = await sync_to_async(redis_client.smembers)(self.online_set)

            await self.send(text_data=json.dumps({
                "type": "presence_snapshot",
                "users": list(map(int, online_users))
            }))

            # optional delivery sync
            await self.mark_all_as_delivered_on_connect()

        except Exception as e:
            print("❌ CONNECT ERROR:", str(e))
            await self.close()

    # =========================
    # DISCONNECT
    # =========================
    async def disconnect(self, close_code):
        try:
            if hasattr(self, "user_group"):
                await self.channel_layer.group_discard(self.user_group, self.channel_name)

            if hasattr(self, "tenant_group"):
                await self.channel_layer.group_discard(self.tenant_group, self.channel_name)

            if hasattr(self, "connection_key"):
                await sync_to_async(redis_client.srem)(
                    self.connection_key,
                    self.socket_id
                )

                count = await sync_to_async(redis_client.scard)(self.connection_key)

                print(f"❌ WS DISCONNECT user={self.membership_id}, count={count}")

                # 🔥 LAST CONNECTION = OFFLINE
                # 🔥 LAST CONNECTION = OFFLINE
                if count == 0:
                    now = timezone.now()

                    # remove from online set
                    await sync_to_async(redis_client.srem)(
                        self.online_set,
                        self.membership_id
                    )

                    # 🔥 STORE LAST SEEN (REDIS)
                    await sync_to_async(redis_client.set)(
                        f"user:{self.membership_id}:last_seen",
                        now.isoformat()
                    )

                    # 🔥 STORE LAST SEEN (DB - CRITICAL)
                    await database_sync_to_async(
                        Membership.objects.filter(id=self.membership_id).update
                    )(last_seen=now)

                    print(f"🔥 BROADCAST OFFLINE {self.membership_id}")

                    # 🔥 PRESENCE UPDATE
                    await self.channel_layer.group_send(
                        self.tenant_group,
                        {
                            "type": "presence_update",
                            "user_id": self.membership_id,
                            "status": "offline"
                        }
                    )

                    # 🔥 LAST SEEN EVENT (NEW)
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

    # =========================
    # RECEIVE
    # =========================
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            t = data.get("type")

            if t == "join_room":
                await self.join_room(data)

            elif t == "leave_room":
                await self.leave_room(data)

            elif t == "message_received":
                await self.handle_message_received(data)

            elif t == "typing_start":
                await self.handle_typing(data, True)

            elif t == "typing_stop":
                await self.handle_typing(data, False)

        except Exception as e:
            print("❌ RECEIVE ERROR:", str(e))

    # =========================
    # JOIN ROOM
    # =========================
    async def join_room(self, data):
        room_id = data.get("room_id")
        if not room_id:
            return

        group = f"tenant_{self.tenant_id}_room_{room_id}"

        await self.channel_layer.group_add(group, self.channel_name)

        await sync_to_async(redis_client.sadd)(
            f"room:{self.tenant_id}:{room_id}",
            self.membership_id
        )

        await self.mark_existing_as_delivered(room_id)

    # =========================
    async def leave_room(self, data):
        room_id = data.get("room_id")
        if not room_id:
            return

        await self.channel_layer.group_discard(
            f"tenant_{self.tenant_id}_room_{room_id}",
            self.channel_name
        )

        await sync_to_async(redis_client.srem)(
            f"room:{self.tenant_id}:{room_id}",
            self.membership_id
        )

    # =========================
    # MESSAGE ACK (DELIVERED)
    # =========================
    async def handle_message_received(self, data):
        message_id = data.get("message_id")
        if not message_id:
            return

        try:
            message = await database_sync_to_async(Message.objects.get)(id=message_id)
        except Message.DoesNotExist:
            return

        now = timezone.now()

        count = await sync_to_async(redis_client.scard)(self.connection_key)
        if count == 0:
            return

        updated = await database_sync_to_async(
            MessageStatus.objects.filter(
                message_id=message.id,
                membership_id=self.membership_id,
                status=MessageStatus.Status.SENT
            ).update
        )(status=MessageStatus.Status.DELIVERED, delivered_at=now)

        if not updated:
            return

        await self.channel_layer.group_send(
            f"tenant_{self.tenant_id}_room_{message.conversation_id}",
            {
                "type": "status_update",
                "room_id": str(message.conversation_id),
                "message_id": str(message.id),
                "status": "delivered",
            }
        )

    # =========================
    # AUTO DELIVERY (JOIN)
    # =========================
    async def mark_existing_as_delivered(self, room_id):
        now = timezone.now()

        message_ids = await database_sync_to_async(list)(
            MessageStatus.objects.filter(
                message__conversation_id=room_id,
                membership_id=self.membership_id,
                status=MessageStatus.Status.SENT,
            ).values_list("message_id", flat=True)
        )

        if not message_ids:
            return

        await database_sync_to_async(
            MessageStatus.objects.filter(
                message_id__in=message_ids,
                membership_id=self.membership_id,
            ).update
        )(status=MessageStatus.Status.DELIVERED, delivered_at=now)

        for msg_id in message_ids:
            await self.channel_layer.group_send(
                f"tenant_{self.tenant_id}_room_{room_id}",
                {
                    "type": "status_update",
                    "room_id": str(room_id),
                    "message_id": str(msg_id),
                    "status": "delivered",
                }
            )

    # =========================
    # AUTO DELIVERY (CONNECT)
    # =========================
    async def mark_all_as_delivered_on_connect(self):
        now = timezone.now()

        message_ids = await database_sync_to_async(list)(
            MessageStatus.objects.filter(
                membership_id=self.membership_id,
                status=MessageStatus.Status.SENT
            ).values_list("message_id", flat=True)
        )

        if not message_ids:
            return

        await database_sync_to_async(
            MessageStatus.objects.filter(
                message_id__in=message_ids,
                membership_id=self.membership_id
            ).update
        )(status=MessageStatus.Status.DELIVERED, delivered_at=now)

        messages = await database_sync_to_async(list)(
            Message.objects.filter(id__in=message_ids).values("id", "conversation_id")
        )

        for msg in messages:
            await self.channel_layer.group_send(
                f"tenant_{self.tenant_id}_room_{msg['conversation_id']}",
                {
                    "type": "status_update",
                    "room_id": str(msg["conversation_id"]),
                    "message_id": str(msg["id"]),
                    "status": "delivered",
                }
            )


    async def handle_typing(self, data, is_typing):
        room_id = data.get("room_id")

        if not room_id:
            return

        group = f"tenant_{self.tenant_id}_room_{room_id}"

        await self.channel_layer.group_send(
            group,
            {
                "type": "typing_event",
                "user_id": self.membership_id,
                "room_id": str(room_id),
                "is_typing": is_typing,
            }
        )

    # =========================
    # EVENTS
    # =========================
    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    async def incoming_message(self, event):
        await self.send(text_data=json.dumps(event))

    async def sidebar_update(self, event):
        await self.send(text_data=json.dumps(event))

    async def status_update(self, event):
        await self.send(text_data=json.dumps(event))

    async def read_receipt(self, event):
        await self.send(text_data=json.dumps(event))

    async def presence_update(self, event):
        await self.send(text_data=json.dumps(event))
    
    async def typing_event(self, event):
        await self.send(text_data=json.dumps(event))
    async def last_seen_update(self, event):
        await self.send(text_data=json.dumps(event))