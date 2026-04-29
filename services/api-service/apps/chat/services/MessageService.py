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
    


from django.utils.dateparse import parse_datetime

class MessageCursorPagination:

    def __init__(self, queryset, cursor=None, limit=20):
        self.queryset = queryset
        self.cursor = cursor
        self.limit = limit

    def paginate(self):
        qs = self.queryset

        if self.cursor:
            cursor_dt = parse_datetime(self.cursor)
            qs = qs.filter(created_at__lt=cursor_dt)

        # fetch newest first
        qs = qs.order_by("-created_at")[: self.limit + 1]

        items = list(qs)

        has_more = len(items) > self.limit
        items = items[: self.limit]

        # reverse for UI (old → new)
        items.reverse()

        next_cursor = (
            items[0].created_at.isoformat()
            if has_more and items
            else None
        )

        return items, next_cursor, has_more