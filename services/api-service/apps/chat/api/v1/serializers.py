from rest_framework import serializers
from apps.chat.models import Conversation, Message, MessageStatus


class ConversationSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    other_participant_id = serializers.SerializerMethodField()
    participant_ids = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "type",
            "display_name",
            "last_message",
            "updated_at",
            "other_participant_id",
            "participant_ids",
            "unread_count",
        ]

    def get_display_name(self, obj):
        request = self.context.get("request")

        if not request or not hasattr(request, "membership"):
            return "User"

        current_membership = request.membership

        if obj.type == Conversation.Type.DIRECT:
            other = (
                obj.participants.exclude(membership=current_membership)
                .select_related("membership__user")
                .only("membership__user__username")
                .first()
            )
            return other.membership.user.username if other else "User"

        if obj.type == Conversation.Type.GROUP:
            return obj.name or "Group Chat"

        if obj.type == Conversation.Type.DEPARTMENT:
            return obj.department.name if obj.department else "Department Chat"

        return "Chat"

    def get_last_message(self, obj):
        return obj.last_message.content if obj.last_message else None

    def get_other_participant_id(self, obj):
        if obj.type == Conversation.Type.DIRECT:
            request = self.context.get("request")
            return (
                obj.participants.exclude(membership=request.membership)
                .values_list("membership_id", flat=True)
                .first()
            )
        return None

    def get_participant_ids(self, obj):
        return list(obj.participants.values_list("membership_id", flat=True))

    def get_unread_count(self, obj):
        request = self.context.get("request")

        if not request or not hasattr(request, "membership"):
            return 0

        membership = request.membership

        return MessageStatus.objects.filter(
            message__conversation=obj,
            membership=membership,
            status__in=[
                MessageStatus.Status.SENT,
                MessageStatus.Status.DELIVERED,
            ],
        ).count()


class MessageSerializer(serializers.ModelSerializer):
    message = serializers.CharField(source="content")
    sender = serializers.IntegerField(source="sender.id")
    status = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "message", "sender", "created_at", "status"]

    def get_status(self, obj):
        request = self.context.get("request", None)

        if not request or not hasattr(request, "membership"):
            return MessageStatus.Status.SENT

        membership = request.membership

        status_obj = obj.statuses.filter(membership=membership).first()
        return status_obj.status if status_obj else MessageStatus.Status.SENT


class DirectChatSerializer(serializers.Serializer):
    target_membership_id = serializers.IntegerField()


class SendMessageSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField()
    content = serializers.CharField()