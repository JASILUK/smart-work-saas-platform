from django.shortcuts import get_object_or_404
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache

from apps.chat.models import (
    Message,
    Conversation,
    ConversationParticipant,
    MessageStatus,
)
from apps.chat.selectors import get_conversation_messages
from apps.core.exceptions import ApplicationError


class MessageService:

    @staticmethod
    def send_message(conversation_id, sender_membership, content):
        conversation = get_object_or_404(Conversation, id=conversation_id)

        # 1. Create the message
        message = Message.objects.create(
            conversation=conversation,
            sender=sender_membership,
            content=content
        )

        participants = ConversationParticipant.objects.filter(
            conversation=conversation
        ).select_related("membership")

        now = timezone.now()

        # 2. Create statuses for all participants
        statuses = []
        for participant in participants:
            if participant.membership_id == sender_membership.id:
                statuses.append(
                    MessageStatus(
                        message=message,
                        membership=participant.membership,
                        status=MessageStatus.Status.READ,
                        delivered_at=now,
                        read_at=now,
                    )
                )
            else:
                statuses.append(
                    MessageStatus(
                        message=message,
                        membership=participant.membership,
                        status=MessageStatus.Status.SENT,
                    )
                )

        MessageStatus.objects.bulk_create(statuses)

        # 3. Check online status for immediate delivery check
        # NOTE: Ensure the cache key here matches what you set in MainConsumer
        online_members = cache.get(f"company_online:{conversation.company_id}") or set()
        delivered_member_ids = []

        for participant in participants:
            if (
                participant.membership_id != sender_membership.id
                and participant.membership_id in online_members
            ):
                updated = MessageStatus.objects.filter(
                    message=message,
                    membership=participant.membership,
                    status=MessageStatus.Status.SENT,
                ).update(
                    status=MessageStatus.Status.DELIVERED,
                    delivered_at=now,
                )
                if updated:
                    delivered_member_ids.append(participant.membership_id)

        # 4. Update conversation metadata
        conversation.last_message = message
        conversation.save(update_fields=["last_message", "updated_at"])

        channel_layer = get_channel_layer()

        # 5. BROADCAST: New Message
        # We include conversation_id so React knows which chat window to update
        async_to_sync(channel_layer.group_send)(
            f"chat_{conversation_id}",
            {
                "type": "chat_message",
                "id": str(message.id),
                "conversation_id": str(conversation_id), 
                "message": message.content,  # Matches serializer 'message' key
                "sender": sender_membership.id,
                "created_at": message.created_at.isoformat(),
                "status": "sent"
            }
        )

        # 6. BROADCAST: Delivered Status
        if delivered_member_ids:
            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation_id}",
                {
                    "type": "status_update",
                    "conversation_id": str(conversation_id),  # Added this
                    "message_id": str(message.id),
                    "status": "delivered",
                }
            )

        # 7. BROADCAST: Sidebar Update
        # Change the group to your company_group name
        async_to_sync(channel_layer.group_send)(
            f"company_{conversation.company_id}",
            {
                "type": "sidebar_update",
                "conversation_id": str(conversation_id),
                "last_message": message.content,
                "updated_at": message.created_at.isoformat(),
                "sender_id": sender_membership.id,
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
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation_id}",
                {
                    "type": "read_receipt",
                    "conversation_id": str(conversation_id),
                    "reader_id": membership.id,
                    "status": "read" # Added for consistency
                }
            )

    @staticmethod
    def get_messages(conversation_id, membership):
        is_member = ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            membership=membership
        ).exists()

        if not is_member:
            raise ApplicationError("Not allowed")

        return get_conversation_messages(conversation_id).prefetch_related("statuses")