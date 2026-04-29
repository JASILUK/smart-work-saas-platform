from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from apps.chat.services.MessageService import MessageCursorPagination
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import F
import redis
from django.conf import settings

from apps.chat.models import (
    Message,
    Conversation,
    ConversationParticipant,
    MessageStatus,
)
from apps.chat.selectors import get_conversation_messages
from apps.core.exceptions import ApplicationError

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

def is_user_online(user_id):
    return redis_client.scard(f"user:{user_id}:connections") > 0


class MessageService:

    # 🔥 ONLY THIS FUNCTION CHANGED — rest stays same

    @staticmethod
    @transaction.atomic
    def send_message(conversation_id, sender_membership, content):
        conversation = get_object_or_404(Conversation, id=conversation_id)

        message = Message.objects.create(
            conversation=conversation,
            sender=sender_membership,
            content=content
        )

        participants = list(
            ConversationParticipant.objects.filter(
                conversation=conversation
            ).select_related("membership")
        )

        now = timezone.now()

        # 🔥 FIX: unread only if NOT in room
        for p in participants:
            if p.membership_id == sender_membership.id:
                continue

            in_room = redis_client.sismember(
                f"room:{conversation.company_id}:{conversation_id}",
                p.membership_id
            )

            if not in_room:
                ConversationParticipant.objects.filter(
                    conversation=conversation,
                    membership_id=p.membership_id
                ).update(
                    unread_count=F("unread_count") + 1
                )

        # statuses
        statuses = []
        for p in participants:
            if p.membership_id == sender_membership.id:
                statuses.append(
                    MessageStatus(
                        message=message,
                        membership=p.membership,
                        status=MessageStatus.Status.READ,
                        delivered_at=now,
                        read_at=now,
                    )
                )
            else:
                statuses.append(
                    MessageStatus(
                        message=message,
                        membership=p.membership,
                        status=MessageStatus.Status.SENT,
                    )
                )

        MessageStatus.objects.bulk_create(statuses)

        conversation.last_message = message
        conversation.save(update_fields=["last_message", "updated_at"])

        channel_layer = get_channel_layer()

        # send message
        async_to_sync(channel_layer.group_send)(
            f"tenant_{conversation.company_id}_room_{conversation_id}",
            {
                "type": "chat_message",
                "id": str(message.id),
                "room_id": str(conversation_id),
                "message": message.content,
                "sender": sender_membership.id,
                "created_at": message.created_at.isoformat(),
                "status": "sent",
            }
        )
  

        for p in participants:
            user_group = f"tenant_{conversation.company_id}_user_{p.membership_id}"

            if p.membership_id != sender_membership.id:

                # ✅ FIXED ONLINE CHECK
                if is_user_online(p.membership_id):

                    MessageStatus.objects.filter(
                        message=message,
                        membership=p.membership
                    ).update(
                        status=MessageStatus.Status.DELIVERED,
                        delivered_at=now
                    )

                    async_to_sync(channel_layer.group_send)(
                        f"tenant_{conversation.company_id}_room_{conversation_id}",
                        {
                            "type": "status_update",
                            "room_id": str(conversation_id),
                            "message_id": str(message.id),
                            "status": "delivered",
                        }
                    )

                async_to_sync(channel_layer.group_send)(
                    user_group,
                    {
                        "type": "incoming_message",
                        "message_id": str(message.id),
                        "room_id": str(conversation_id),
                    }
                )

            async_to_sync(channel_layer.group_send)(
                user_group,
                {
                    "type": "sidebar_update",
                    "conversation_id": str(conversation_id),
                    "last_message": message.content,
                    "updated_at": message.created_at.isoformat(),
                    "sender": sender_membership.id,
                    "is_unread": p.membership_id != sender_membership.id
                }
            )

        return message

    @staticmethod
    def mark_conversation_as_read(conversation_id, membership):
        now = timezone.now()

        updated = MessageStatus.objects.filter(
            message__conversation_id=conversation_id,
            membership=membership,
            status__in=[
                MessageStatus.Status.SENT,
                MessageStatus.Status.DELIVERED,
            ],
        ).update(
            status=MessageStatus.Status.READ,
            read_at=now,
        )

        if updated > 0:
            ConversationParticipant.objects.filter(
                conversation_id=conversation_id,
                membership=membership
            ).update(unread_count=0)

            channel_layer = get_channel_layer()

            # 🔥 FIXED EVENT
            async_to_sync(channel_layer.group_send)(
                f"tenant_{membership.company_id}_room_{conversation_id}",
                {
                    "type": "read_receipt",
                    "room_id": str(conversation_id),
                    "message_id": "ALL",   # ✅ CRITICAL FIX
                    "reader_id": membership.id,
                }
            )

            # sidebar update
            async_to_sync(channel_layer.group_send)(
                f"tenant_{membership.company_id}_user_{membership.id}",
                {
                    "type": "sidebar_update",
                    "conversation_id": str(conversation_id),
                    "last_message": None,
                    "updated_at": timezone.now().isoformat(),
                    "sender": membership.id,
                    "is_unread": False,
                    "force_unread_reset": True
                }
            )



    @staticmethod
    def get_paginated_messages(conversation_id, membership, cursor=None, limit=20):
        queryset = MessageService.get_messages(
            conversation_id=conversation_id,
            membership=membership,
        )

        paginator = MessageCursorPagination(
            queryset=queryset,
            cursor=cursor,
            limit=limit,
        )

        return paginator.paginate()
    
    @staticmethod
    def get_messages(conversation_id, membership):
        is_member = ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            membership=membership
        ).exists()

        if not is_member:
            raise ApplicationError("Not allowed")

        return get_conversation_messages(conversation_id).prefetch_related("statuses")