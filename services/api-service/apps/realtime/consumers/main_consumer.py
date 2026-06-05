import json
from channels.generic.websocket import AsyncWebsocketConsumer
from apps.chat.models import ConversationParticipant
from asgiref.sync import sync_to_async
from apps.companies.models import Membership
from django.core.cache import cache

class MainConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]

        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        # Get membership_id from the URL route
        membership_id = self.scope["url_route"]["kwargs"]["membership_id"]
        self.membership = await self.get_membership(membership_id)

        if not self.membership:
            await self.close()
            return

        self.membership_id = self.membership.id
        self.company_id = self.membership.company_id

        # 1. User and Company Groups (Always connected)
        self.user_group = f"user_{self.membership_id}"
        self.company_group = f"company_{self.company_id}"
        
        # Track the active chat room to avoid multiple subscriptions
        self.active_chat_group = None 

        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.channel_layer.group_add(self.company_group, self.channel_name)

        await self.set_online(True)

        await self.channel_layer.group_send(
            self.company_group,
            {
                "type": "presence_update",
                "membership_id": self.membership_id,
                "status": "online"
            }
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.set_online(False)
        await self.channel_layer.group_discard(self.user_group, self.channel_name)
        await self.channel_layer.group_discard(self.company_group, self.channel_name)
        
        await self.channel_layer.group_send(
            self.company_group,
            {
                "type": "presence_update",
                "membership_id": self.membership_id,
                "status": "offline"
            }
        )
        
        if self.active_chat_group:
            await self.channel_layer.group_discard(self.active_chat_group, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data.get("type")

        if event_type == "join_chat":
            await self.handle_join_chat(data.get("conversation_id"))

    # ================= ROOM MANAGEMENT =================

    async def handle_join_chat(self, conversation_id):
        # Leave previous chat group if it exists
        if self.active_chat_group:
            await self.channel_layer.group_discard(self.active_chat_group, self.channel_name)

        is_member = await self.check_conversation(conversation_id)
        if not is_member:
            return

        # Join new chat group
        self.active_chat_group = f"chat_{conversation_id}"
        await self.channel_layer.group_add(self.active_chat_group, self.channel_name)

    # ================= EVENT HANDLERS =================
    # These functions MUST exist to handle messages from MessageService

    async def chat_message(self, event):
        """Called when MessageService sends 'type': 'chat_message'"""
        await self.send(text_data=json.dumps(event))

    async def sidebar_update(self, event):
        """Called when MessageService sends 'type': 'sidebar_update'"""
        await self.send(text_data=json.dumps(event))

    async def status_update(self, event):
        """Called when MessageService sends 'type': 'status_update'"""
        await self.send(text_data=json.dumps(event))

    async def read_receipt(self, event):
        """Called when MessageService sends 'type': 'read_receipt'"""
        await self.send(text_data=json.dumps(event))

    # ================= HELPERS =================

    @sync_to_async
    def get_membership(self, membership_id):
        return Membership.objects.filter(
            id=membership_id,
            user=self.user,
            is_active=True
        ).select_related("company").first()

    @sync_to_async
    def check_conversation(self, conversation_id):
        return ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            membership_id=self.membership_id
        ).exists()

    @sync_to_async
    def set_online(self, is_online):
        membership_key = f"online:membership:{self.membership_id}"
        company_key = f"company_online:{self.company_id}"

        if is_online:
            cache.set(membership_key, True, timeout=60)
            online_set = cache.get(company_key) or set()
            online_set.add(self.membership_id)
            cache.set(company_key, online_set, timeout=3600)
        else:
            cache.delete(membership_key)
            online_set = cache.get(company_key) or set()
            online_set.discard(self.membership_id)
            cache.set(company_key, online_set, timeout=3600)