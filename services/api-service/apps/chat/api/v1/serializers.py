from rest_framework import serializers
from apps.chat.models import Conversation, Message, MessageStatus


class ConversationSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    other_membership_id = serializers.SerializerMethodField()
    participant_ids = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    my_membership_id = serializers.SerializerMethodField()

    # 🔥 ADD THIS
    last_seen = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "type",
            "display_name",
            "last_message",
            "updated_at",
            "other_membership_id",
            "participant_ids",
            "unread_count",
            "my_membership_id",
            "last_seen",  # 🔥 ADD
        ]

    def get_last_seen(self, obj):
        request = self.context.get("request")

        if not request or not hasattr(request, "membership"):
            return None

        if obj.type != Conversation.Type.DIRECT:
            return None

        other = (
            obj.participants.exclude(membership=request.membership)
            .select_related("membership")
            .only("membership__last_seen")
            .first()
        )

        return other.membership.last_seen if other else None
    

    def get_other_membership_id(self, obj):  # ✅ renamed
        if obj.type == Conversation.Type.DIRECT:
            request = self.context.get("request")
            return (
                obj.participants.exclude(membership=request.membership)
                .values_list("membership_id", flat=True)
                .first()
            )
        return None

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

    

    def get_participant_ids(self, obj):
        return list(obj.participants.values_list("membership_id", flat=True))

    def get_unread_count(self, obj):
        request = self.context.get("request")

        if not request or not hasattr(request, "membership"):
            return 0

        participant = obj.participants.filter(
            membership=request.membership
        ).first()

        return participant.unread_count if participant else 0

    def get_my_membership_id(self, obj):
        request = self.context.get("request")
        return request.membership.id if request and hasattr(request, "membership") else None


class MessageSerializer(serializers.ModelSerializer):
    message = serializers.CharField(source="content")
    sender = serializers.IntegerField(source="sender.id")
    status = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "message", "sender", "created_at", "status"]

    def get_status(self, obj):
        request = self.context.get("request")

        if not request or not hasattr(request, "membership"):
            return MessageStatus.Status.SENT

        me = request.membership

        # If not my message → no status
        if obj.sender_id != me.id:
            return None

        statuses = obj.statuses.exclude(membership=me)

        total = statuses.count()

        if total == 0:
            return MessageStatus.Status.SENT

        read_count = statuses.filter(status=MessageStatus.Status.READ).count()

        if read_count == total:
            return MessageStatus.Status.READ

        delivered_count = statuses.filter(
            status=MessageStatus.Status.DELIVERED
        ).count()

        if delivered_count > 0:
            return MessageStatus.Status.DELIVERED

        return MessageStatus.Status.SENT


class DirectChatSerializer(serializers.Serializer):
    target_membership_id = serializers.IntegerField()


class SendMessageSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField()
    content = serializers.CharField()