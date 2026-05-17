from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.chat.models import (
    Conversation,
    ConversationParticipant,
)

from apps.chat.selectors import (
    get_direct_conversation,
    get_user_conversations,
)

from apps.companies.models import Membership


class ChatService:

    # =====================================================
    # CREATE OR GET DIRECT CONVERSATION
    # =====================================================

    @staticmethod
    @transaction.atomic
    def get_or_create_direct_conversation(
        *,
        current_membership,
        target_membership_id,
    ):

        company = current_membership.company

        target = get_object_or_404(

            Membership,

            id=target_membership_id,

            company=company,
        )

        # =================================================
        # PREVENT SELF CHAT
        # =================================================

        if target.id == current_membership.id:

            raise Exception(
                "Cannot chat with yourself"
            )

        # =================================================
        # CHECK EXISTING CONVERSATION
        # =================================================

        conversation = get_direct_conversation(

            company=company,

            membership1=current_membership,

            membership2=target,
        )

        if conversation:

            return conversation

        # =================================================
        # CREATE CONVERSATION
        # =================================================

        conversation = Conversation.objects.create(

            company=company,

            type=Conversation.Type.DIRECT,

            created_by=current_membership.user,
        )

        # =================================================
        # CREATE PARTICIPANTS
        # =================================================

        ConversationParticipant.objects.bulk_create([

            ConversationParticipant(

                conversation=conversation,

                membership=current_membership,
            ),

            ConversationParticipant(

                conversation=conversation,

                membership=target,
            ),
        ])

        return conversation

    # =====================================================
    # LIST USER CONVERSATIONS
    # =====================================================

    @staticmethod
    def list_conversations(
        *,
        membership,
        search="",
        conversation_type="all",
    ):

        return get_user_conversations(
            membership=membership,
            search=search,
            conversation_type=conversation_type,
        )