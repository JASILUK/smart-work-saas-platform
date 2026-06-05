import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from apps.chat.models import ConversationParticipant


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]

        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.group_name = f"chat_{self.conversation_id}"

        is_member = await self.check_membership()
        if not is_member:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "id": event["id"],
            "message": event["message"],
            "sender": event["sender"],
            "created_at": event["created_at"],
        }))

    async def status_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "status_update",
            "message_id": event["message_id"],
            "status": event["status"],
        }))

    async def read_receipt(self, event):
        await self.send(text_data=json.dumps({
            "type": "read_receipt",
            "conversation_id": event["conversation_id"],
            "reader_id": event["reader_id"],
        }))

    async def receive(self, text_data):
        # No frontend-driven delivery needed now.
        # Delivery is controlled by backend presence + send_message logic.
        pass

    @sync_to_async
    def check_membership(self):
        return ConversationParticipant.objects.filter(
            conversation_id=self.conversation_id,
            membership__user=self.user
        ).exists()