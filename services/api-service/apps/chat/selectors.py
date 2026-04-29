from apps.chat.models import Conversation, Message
from django.db.models import Count


def get_direct_conversation(company, membership1, membership2):
    return (
        Conversation.objects
        .filter(company=company, type=Conversation.Type.DIRECT)
        .annotate(p_count=Count("participants"))
        .filter(
            p_count=2,
            participants__membership=membership1
        )
        .filter(
            participants__membership=membership2
        )
        .first()
    )



def get_user_conversations(membership):
    return (
        Conversation.objects
        .filter(participants__membership=membership)
        .select_related("last_message", "department")
        .prefetch_related("participants__membership__user")
        .order_by("-updated_at")  # 🔥 FIXED
    )


def get_conversation_messages(conversation_id):
    return (
        Message.objects
        .filter(conversation_id=conversation_id, deleted=False)
        .select_related("sender", "sender__user")
        .prefetch_related("statuses")
        .order_by("created_at")   # 🔥 FIXED
    )