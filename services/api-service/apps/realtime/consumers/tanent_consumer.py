from channels.generic.websocket import (
    AsyncWebsocketConsumer,
)

from channels.db import (
    database_sync_to_async,
)

from django.utils import timezone
from django.conf import settings

from apps.meetings.realtime.meeting_chat_handler import MeetingChatRealtimeHandler
from apps.meetings.realtime.meeting_handlers import MeetingRealtimeHandler
from asgiref.sync import sync_to_async

from apps.chat.realtime.handlers import (
    ChatRealtimeHandler,
)

from apps.companies.models import (
    Membership,
)

import redis
import json


redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


class TenantConsumer(
    AsyncWebsocketConsumer,
):

    # =====================================================
    # CONNECT
    # =====================================================

    async def connect(self):

        try:

            user = self.scope.get("user")

            tenant_id = self.scope.get(
                "tenant_id"
            )

            membership = self.scope.get(
                "membership"
            )

            if (
                not user
                or user.is_anonymous
                or not tenant_id
                or not membership
            ):
                await self.close()
                return

            self.user = user

            self.username = (
                user.username
            )
            
            self.tenant_id = tenant_id

            self.membership_id = (
                membership.id
            )

            self.socket_id = (
                self.channel_name
            )

            # =============================================
            # ACTIVE MEETING TRACKER
            # =============================================

            self.active_meetings = set()

            self.user_group = (
                f"tenant_{tenant_id}"
                f"_user_{self.membership_id}"
            )

            self.tenant_group = (
                f"tenant_{tenant_id}"
            )

            self.connection_key = (
                f"user:{self.membership_id}"
                f":connections"
            )

            self.online_set = (
                f"online_users:{self.tenant_id}"
            )

            # =============================================
            # JOIN GROUPS
            # =============================================

            await self.channel_layer.group_add(
                self.user_group,
                self.channel_name,
            )

            await self.channel_layer.group_add(
                self.tenant_group,
                self.channel_name,
            )

            await self.accept()

            # =============================================
            # TRACK SOCKET
            # =============================================

            await sync_to_async(
                redis_client.sadd
            )(
                self.connection_key,
                self.socket_id,
            )

            count = await sync_to_async(
                redis_client.scard
            )(
                self.connection_key
            )

            print(
                f"✅ WS CONNECTED "
                f"user={self.membership_id}, "
                f"count={count}"
            )

            # =============================================
            # FIRST CONNECTION
            # =============================================

            if count == 1:

                await sync_to_async(
                    redis_client.sadd
                )(
                    self.online_set,
                    self.membership_id,
                )

                await self.channel_layer.group_send(
                    self.tenant_group,
                    {
                        "type": "presence_update",
                        "user_id": (
                            self.membership_id
                        ),
                        "status": "online",
                    }
                )

            # =============================================
            # PRESENCE SNAPSHOT
            # =============================================

            online_users = await sync_to_async(
                redis_client.smembers
            )(
                self.online_set
            )

            await self.send(
                text_data=json.dumps(
                    {
                        "type": (
                            "presence_snapshot"
                        ),
                        "users": list(
                            map(
                                int,
                                online_users,
                            )
                        ),
                    }
                )
            )

            # =============================================
            # DELIVERY SYNC
            # =============================================

            chat_handler = (
                ChatRealtimeHandler(
                    consumer=self,
                )
            )

            await (
                chat_handler
                .mark_all_as_delivered_on_connect()
            )

        except Exception as e:

            print(
                "❌ CONNECT ERROR:",
                str(e),
            )

            await self.close()

    # =====================================================
    # DISCONNECT
    # =====================================================

    async def disconnect(
        self,
        close_code,
    ):

        try:

            # =============================================
            # CLEANUP ACTIVE MEETINGS
            # =============================================

            if hasattr(
                self,
                "active_meetings",
            ):

                meeting_handler = (
                    MeetingRealtimeHandler(
                        consumer=self,
                    )
                )

                for meeting_id in list(
                    self.active_meetings
                ):

                    try:

                        await meeting_handler.leave_meeting(
                            data={
                                "meeting_id": meeting_id,
                            }
                        )

                    except Exception as e:

                        print(
                            "❌ MEETING CLEANUP ERROR:",
                            str(e),
                        )

            if hasattr(
                self,
                "user_group",
            ):

                await self.channel_layer.group_discard(
                    self.user_group,
                    self.channel_name,
                )

            if hasattr(
                self,
                "tenant_group",
            ):

                await self.channel_layer.group_discard(
                    self.tenant_group,
                    self.channel_name,
                )

            if hasattr(
                self,
                "connection_key",
            ):

                await sync_to_async(
                    redis_client.srem
                )(
                    self.connection_key,
                    self.socket_id,
                )

                count = await sync_to_async(
                    redis_client.scard
                )(
                    self.connection_key
                )

                print(
                    f"❌ WS DISCONNECT "
                    f"user={self.membership_id}, "
                    f"count={count}"
                )

                if count == 0:

                    now = timezone.now()

                    # =====================================
                    # REMOVE ONLINE
                    # =====================================

                    await sync_to_async(
                        redis_client.srem
                    )(
                        self.online_set,
                        self.membership_id,
                    )

                    # =====================================
                    # LAST SEEN REDIS
                    # =====================================

                    await sync_to_async(
                        redis_client.set
                    )(
                        (
                            f"user:"
                            f"{self.membership_id}"
                            f":last_seen"
                        ),
                        now.isoformat(),
                    )

                    # =====================================
                    # LAST SEEN DB
                    # =====================================

                    await database_sync_to_async(
                        Membership.objects.filter(
                            id=self.membership_id
                        ).update
                    )(
                        last_seen=now
                    )

                    # =====================================
                    # BROADCAST OFFLINE
                    # =====================================

                    await self.channel_layer.group_send(
                        self.tenant_group,
                        {
                            "type": (
                                "presence_update"
                            ),
                            "user_id": (
                                self.membership_id
                            ),
                            "status": "offline",
                        }
                    )

                    await self.channel_layer.group_send(
                        self.tenant_group,
                        {
                            "type": (
                                "last_seen_update"
                            ),
                            "user_id": (
                                self.membership_id
                            ),
                            "last_seen": (
                                now.isoformat()
                            ),
                        }
                    )

        except Exception as e:

            print(
                "❌ DISCONNECT ERROR:",
                str(e),
            )

    # =====================================================
    # RECEIVE
    # =====================================================

    async def receive(
        self,
        text_data,
    ):

        try:

            data = json.loads(
                text_data
            )

            event_type = data.get(
                "type"
            )

            # =============================================
            # CHAT ROOM EVENTS
            # =============================================

            if event_type == "join_room":

                await self.join_room(
                    data=data,
                )

            elif event_type == "leave_room":

                await self.leave_room(
                    data=data,
                )

            # =============================================
            # MEETING EVENTS
            # =============================================

            elif event_type in [
                "join_meeting",
                "leave_meeting",
            ]:

                meeting_handler = (
                    MeetingRealtimeHandler(
                        consumer=self,
                    )
                )

                await meeting_handler.handle(
                    data=data,
                )

            # =============================================
            # MEETING CHAT EVENTS
            # =============================================

            elif event_type in [
            "meeting_message",
            "meeting_typing",
            "meeting_chat_snapshot",
            ]:

                

                meeting_chat_handler = (
                    MeetingChatRealtimeHandler(
                        consumer=self,
                    )
                )

                await meeting_chat_handler.handle(
                    data=data,
                )
            # =============================================
            # CHAT REALTIME EVENTS
            # =============================================

            else:

                chat_handler = (
                    ChatRealtimeHandler(
                        consumer=self,
                    )
                )

                await chat_handler.handle(
                    data=data,
                )

        except Exception as e:

            print(
                "❌ RECEIVE ERROR:",
                str(e),
            )

    # =====================================================
    # JOIN ROOM
    # =====================================================

    async def join_room(
        self,
        *,
        data,
    ):

        room_id = data.get("room_id")

        if not room_id:
            return

        room_group = (
            f"tenant_{self.tenant_id}"
            f"_room_{room_id}"
        )

        await self.channel_layer.group_add(
            room_group,
            self.channel_name,
        )

        await sync_to_async(
            redis_client.sadd
        )(
            f"room:{self.tenant_id}:{room_id}",
            self.membership_id,
        )

        chat_handler = (
            ChatRealtimeHandler(
                consumer=self,
            )
        )

        await (
            chat_handler
            .mark_room_messages_as_read(
                room_id=room_id,
            )
        )

    # =====================================================
    # LEAVE ROOM
    # =====================================================

    async def leave_room(
        self,
        *,
        data,
    ):

        room_id = data.get("room_id")

        if not room_id:
            return

        await self.channel_layer.group_discard(
            (
                f"tenant_{self.tenant_id}"
                f"_room_{room_id}"
            ),
            self.channel_name,
        )

        await sync_to_async(
            redis_client.srem
        )(
            f"room:{self.tenant_id}:{room_id}",
            self.membership_id,
        )

    # =====================================================
    # EVENTS
    # =====================================================

    async def chat_message(
        self,
        event,
    ):

        await self.send(
            text_data=json.dumps(event)
        )

    async def incoming_message(
        self,
        event,
    ):

        await self.send(
            text_data=json.dumps(event)
        )

    async def sidebar_update(
        self,
        event,
    ):

        await self.send(
            text_data=json.dumps(event)
        )

    async def status_update(
        self,
        event,
    ):

        await self.send(
            text_data=json.dumps(event)
        )

    async def presence_update(
        self,
        event,
    ):

        await self.send(
            text_data=json.dumps(event)
        )

    async def typing_event(
        self,
        event,
    ):

        await self.send(
            text_data=json.dumps(event)
        )

    async def last_seen_update(
        self,
        event,
    ):

        await self.send(
            text_data=json.dumps(event)
        )

    async def message_deleted(
        self,
        event,
    ):

        await self.send(
            text_data=json.dumps(event)
        )

    async def message_edited(
        self,
        event,
    ):

        await self.send(
            text_data=json.dumps(event)
        )

    async def conversation_created(
        self,
        event,
    ):

        await self.send(
            text_data=json.dumps(event)
        )

    async def meeting_presence_snapshot(
        self,
        event,
    ):

        await self.send(
            text_data=json.dumps(event)
        )


    async def participant_joined(
        self,
        event,
    ):

        await self.send(
            text_data=json.dumps(event)
        )


    async def participant_left(
        self,
        event,
    ):

        await self.send(
            text_data=json.dumps(event)
        )


    async def meeting_ended(
        self,
        event,
    ):

        await self.send(
            text_data=json.dumps(event)
        )

    # =====================================================
    # MEETING CHAT EVENTS
    # =====================================================

    async def meeting_message(
        self,
        event,
    ):

        await self.send(
            text_data=json.dumps(event)
        )


    async def meeting_typing(
        self,
        event,
    ):

        await self.send(
            text_data=json.dumps(event)
        )


    async def meeting_chat_snapshot(
        self,
        event,
    ):

        await self.send(
            text_data=json.dumps(event)
        )






