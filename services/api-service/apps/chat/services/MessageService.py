from django.shortcuts import get_object_or_404
from apps.chat.models import Message, Conversation


class ChatService:

    @staticmethod
    def create_message(conversation_id, sender_membership, content):
        conversation = get_object_or_404(Conversation, id=conversation_id)

        message = Message.objects.create(
            conversation=conversation,
            sender=sender_membership,
            content=content
        )

        # update last message (important for UI)
        conversation.last_message = message
        conversation.save(update_fields=["last_message", "updated_at"])

        return message