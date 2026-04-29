
from channels.generic.websocket import AsyncWebsocketConsumer


class PlatformConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope["user"]

        if not user or user.is_anonymous:
            await self.close()
            return

        # 🔐 ensure platform role
        profile = getattr(user, "platform_profile", None)

        if not profile or not profile.is_active:
            await self.close()
            return


        self.user = user

        # groups
        self.user_group = f"platform_user_{user.id}"
        self.global_group = "platform_global"

        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.channel_layer.group_add(self.global_group, self.channel_name)

        await self.accept()

    

    async def disconnect(self, close_code):

        await self.channel_layer.group_discard(
            self.user_group, self.channel_name
        )
        await self.channel_layer.group_discard(
            self.global_group, self.channel_name
        )