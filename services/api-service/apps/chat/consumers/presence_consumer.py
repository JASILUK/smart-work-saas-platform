from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async, async_to_sync
from apps.companies.models import Membership
from apps.chat.models import MessageStatus
from django.utils import timezone
from channels.layers import get_channel_layer
from django.core.cache import cache
import json


class PresenceConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]

        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.membership_id = self.scope["url_route"]["kwargs"]["membership_id"]

        membership = await sync_to_async(Membership.objects.select_related("company").get)(
            id=self.membership_id
        )
        self.company_id = membership.company_id

        self.group_name = f"presence_company_{self.company_id}"
        self.redis_key = f"online_members_co_{self.company_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        online = cache.get(self.redis_key) or set()
        online.add(self.membership_id)
        cache.set(self.redis_key, online, timeout=3600)

        # When user opens app anywhere, mark all pending SENT messages as DELIVERED
        await self.mark_all_as_delivered()

        await self.send(text_data=json.dumps({
            "type": "initial_presence",
            "online_members": list(online),
        }))

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "presence_update",
                "membership_id": self.membership_id,
                "status": "online",
            }
        )

    async def disconnect(self, close_code):
        online = cache.get(self.redis_key) or set()
        online.discard(self.membership_id)
        cache.set(self.redis_key, online, timeout=3600)

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "presence_update",
                "membership_id": self.membership_id,
                "status": "offline",
            }
        )

        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def presence_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "presence_update",
            "membership_id": event["membership_id"],
            "status": event["status"],
        }))

    async def sidebar_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "sidebar_update",
            "conversation_id": event["conversation_id"],
            "last_message": event["last_message"],
            "updated_at": event["updated_at"],
            "sender_id": event.get("sender_id"),
            "message_id": event.get("message_id"),
        }))

    @sync_to_async
    def mark_all_as_delivered(self):
        now = timezone.now()

        pending = MessageStatus.objects.filter(
            membership_id=self.membership_id,
            status=MessageStatus.Status.SENT,
        ).select_related("message")

        channel_layer = get_channel_layer()

        for status_row in pending:
            status_row.status = MessageStatus.Status.DELIVERED
            status_row.delivered_at = now
            status_row.save(update_fields=["status", "delivered_at"])

            async_to_sync(channel_layer.group_send)(
                f"chat_{status_row.message.conversation_id}",
                {
                    "type": "status_update",
                    "message_id": str(status_row.message_id),
                    "status": "delivered",
                }
            )