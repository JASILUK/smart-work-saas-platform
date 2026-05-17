from django.db.models import Count
from django.db.models import Q

from apps.chat.models import (
    Conversation,
    Message,
)


# =====================================================
# GET DIRECT CONVERSATION
# =====================================================

def get_direct_conversation(
    *,
    company,
    membership1,
    membership2,
):

    return (
        Conversation.objects
        .filter(
            company=company,
            type=Conversation.Type.DIRECT,
        )
        .annotate(
            participant_count=Count(
                "participants",
                distinct=True,
            )
        )
        .filter(
            participant_count=2,
            participants__membership=membership1,
        )
        .filter(
            participants__membership=membership2,
        )
        .distinct()
        .first()
    )





# =====================================================
# GET USER CONVERSATIONS
# =====================================================

def get_user_conversations(
    *,
    membership,
    search="",
    conversation_type="all",
):

    queryset = (
        Conversation.objects
        .filter(
            participants__membership=membership,
        )
        .select_related(
            "company",
            "created_by",
            "last_message",
            "managed_department",
        )
        .prefetch_related(
            "participants",
            "participants__membership",
            "participants__membership__user",
        )
    )

    # =================================================
    # SEARCH
    # =================================================

    if search:

        queryset = queryset.filter(

            Q(name__icontains=search)

            |

            Q(
                last_message__content__icontains=search
            )
        )

    # =================================================
    # TYPE FILTER
    # =================================================

    valid_types = {
        Conversation.Type.DIRECT,
        Conversation.Type.GROUP,
        Conversation.Type.DEPARTMENT,
        Conversation.Type.PROJECT,
    }

    if (
        conversation_type != "all"
        and
        conversation_type in valid_types
    ):

        queryset = queryset.filter(
            type=conversation_type,
        )

    # =================================================
    # FINAL
    # =================================================

    return (
        queryset
        .distinct()
        .order_by(
            "-updated_at",
        )
    )

# =====================================================
# GET CONVERSATION MESSAGES
# =====================================================

def get_conversation_messages(
    *,
    conversation_id,
):

    return (
        Message.objects
        .filter(
            conversation_id=conversation_id,
            deleted=False,
        )
        .select_related(
            "sender",
            "sender__user",
            "reply_to",
        )
        .prefetch_related(
            "statuses",
        )
        .order_by(
            "created_at",
        )
    )