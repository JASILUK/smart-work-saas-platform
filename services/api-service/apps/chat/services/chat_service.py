from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.chat.models import Conversation, ConversationParticipant
from apps.chat.selectors import get_direct_conversation, get_user_conversations
from apps.companies.models import Membership


class ChatService:

    @staticmethod
    @transaction.atomic
    def get_or_create_direct_conversation(current_membership, target_membership_id):

        company = current_membership.company

        target = get_object_or_404(
            Membership,
            id=target_membership_id,
            company=company
        )

        if target.id == current_membership.id:
            raise Exception("Cannot chat with yourself")

        conversation = get_direct_conversation(
            company=company,
            membership1=current_membership,
            membership2=target
        )

        if conversation:
            return conversation

        conversation = Conversation.objects.create(
            company=company,
            type=Conversation.Type.DIRECT,
            created_by=current_membership.user
        )

        ConversationParticipant.objects.bulk_create([
            ConversationParticipant(
                conversation=conversation,
                membership=current_membership
            ),
            ConversationParticipant(
                conversation=conversation,
                membership=target
            )
        ])

        return conversation
    
    @staticmethod
    def list_conversations(membership):
        return get_user_conversations(membership)
    