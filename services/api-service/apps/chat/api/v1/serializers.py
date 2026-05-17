from rest_framework import serializers

from apps.chat.models import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageStatus,
)

from apps.chat.services.message_service import MessageService


# =====================================================
# CONVERSATION MEMBER SERIALIZER
# =====================================================

class ConversationMemberSerializer(
    serializers.ModelSerializer
):

    name = serializers.CharField(
        source="membership.user.username",
        read_only=True,
    )

    avatar = serializers.SerializerMethodField()

    class Meta:

        model = ConversationParticipant

        fields = [
            "membership_id",
            "name",
            "avatar",
        ]

    def get_avatar(
        self,
        obj,
    ):

        profile = getattr(
            obj.membership.user,
            "profile",
            None,
        )

        if (
            profile and
            profile.avatar
        ):

            return profile.avatar.url

        return None


# =====================================================
# CONVERSATION SERIALIZER
# =====================================================

class ConversationSerializer(
    serializers.ModelSerializer
):

    display_name = serializers.SerializerMethodField()

    last_message = serializers.SerializerMethodField()

    other_membership_id = (
        serializers.SerializerMethodField()
    )

    participant_ids = (
        serializers.SerializerMethodField()
    )

    unread_count = (
        serializers.SerializerMethodField()
    )

    my_membership_id = (
        serializers.SerializerMethodField()
    )

    last_seen = (
        serializers.SerializerMethodField()
    )

    members = (
        serializers.SerializerMethodField()
    )

    member_count = (
        serializers.SerializerMethodField()
    )

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
            "last_seen",
            "members",
            "member_count",
        ]

    # =====================================================
    # MEMBERS
    # =====================================================

    def get_members(
        self,
        obj,
    ):

        participants = (
            obj.participants
            .select_related(
                "membership",
                "membership__user",
            )
            .all()
        )

        return (
            ConversationMemberSerializer(
                participants,
                many=True,
            ).data
        )

    # =====================================================
    # LAST SEEN
    # =====================================================

    def get_last_seen(
        self,
        obj,
    ):

        request = self.context.get(
            "request"
        )

        if (
            not request or
            not hasattr(
                request,
                "membership",
            )
        ):

            return None

        if (
            obj.type !=
            Conversation.Type.DIRECT
        ):

            return None

        other_participant = (
            obj.participants
            .exclude(
                membership=request.membership
            )
            .select_related(
                "membership",
            )
            .only(
                "membership__last_seen",
            )
            .first()
        )

        if not other_participant:
            return None

        return (
            other_participant
            .membership
            .last_seen
        )

    # =====================================================
    # OTHER MEMBERSHIP ID
    # =====================================================

    def get_other_membership_id(
        self,
        obj,
    ):

        if (
            obj.type !=
            Conversation.Type.DIRECT
        ):

            return None

        request = self.context.get(
            "request"
        )

        if (
            not request or
            not hasattr(
                request,
                "membership",
            )
        ):

            return None

        return (
            obj.participants
            .exclude(
                membership=request.membership
            )
            .values_list(
                "membership_id",
                flat=True,
            )
            .first()
        )

    # =====================================================
    # DISPLAY NAME
    # =====================================================

    def get_display_name(
        self,
        obj,
    ):

        request = self.context.get(
            "request"
        )

        if (
            not request or
            not hasattr(
                request,
                "membership",
            )
        ):

            return "Chat"

        current_membership = (
            request.membership
        )

        # =================================================
        # DIRECT CHAT
        # =================================================

        if (
            obj.type ==
            Conversation.Type.DIRECT
        ):

            other_participant = (
                obj.participants
                .exclude(
                    membership=current_membership
                )
                .select_related(
                    "membership__user",
                )
                .only(
                    "membership__user__username",
                )
                .first()
            )

            if not other_participant:
                return "User"

            return (
                other_participant
                .membership
                .user
                .username
            )

        # =================================================
        # GROUP CHAT
        # =================================================

        if (
            obj.type ==
            Conversation.Type.GROUP
        ):

            return (
                obj.name
                or "Group Chat"
            )

        # =================================================
        # DEPARTMENT CHAT
        # =================================================

        if (
            obj.type ==
            Conversation.Type.DEPARTMENT
        ):

            department = getattr(
                obj,
                "managed_department",
                None,
            )

            return (
                department.name
                if department
                else "Department Chat"
            )

        return "Chat"

    # =====================================================
    # LAST MESSAGE
    # =====================================================

    def get_last_message(
        self,
        obj,
    ):

        if not obj.last_message:
            return None

        return obj.last_message.content

    # =====================================================
    # PARTICIPANT IDS
    # =====================================================

    def get_participant_ids(
        self,
        obj,
    ):

        return list(
            obj.participants.values_list(
                "membership_id",
                flat=True,
            )
        )

    # =====================================================
    # UNREAD COUNT
    # =====================================================

    def get_unread_count(
        self,
        obj,
    ):

        request = self.context.get(
            "request"
        )

        if (
            not request or
            not hasattr(
                request,
                "membership",
            )
        ):

            return 0

        participant = (
            obj.participants
            .filter(
                membership=request.membership,
            )
            .first()
        )

        if not participant:
            return 0

        return participant.unread_count

    # =====================================================
    # MY MEMBERSHIP ID
    # =====================================================

    def get_my_membership_id(
        self,
        obj,
    ):

        request = self.context.get(
            "request"
        )

        if (
            not request or
            not hasattr(
                request,
                "membership",
            )
        ):

            return None

        return request.membership.id

    # =====================================================
    # MEMBER COUNT
    # =====================================================

    def get_member_count(
        self,
        obj,
    ):

        return (
            obj.participants.count()
        )

class MessageSerializer(serializers.ModelSerializer):

    message = serializers.SerializerMethodField()

    sender = serializers.SerializerMethodField()

    status = serializers.SerializerMethodField()

    deleted = serializers.BooleanField()

    edited = serializers.SerializerMethodField()

    reply = serializers.SerializerMethodField()

    class Meta:

        model = Message

        fields = [
            "id",
            "message",
            "message_type",
            "system_event_type",

            "file_url",
            "mime_type",
            "file_name",
            "duration",

            "sender",

            "created_at",

            "status",

            "deleted",
            "edited",

            "reply",

            "metadata",
        ]

    # =====================================================
    # MESSAGE CONTENT
    # =====================================================
    def get_message(self, obj):

        if obj.deleted:
            return "This message was deleted"

        if obj.message_type == Message.MessageType.TEXT:
            return obj.content

        if obj.message_type == Message.MessageType.SYSTEM:
            return obj.content

        if obj.message_type == Message.MessageType.IMAGE:
            return "📷 Photo"

        if obj.message_type == Message.MessageType.VIDEO:
            return "🎥 Video"

        if obj.message_type == Message.MessageType.AUDIO:
            return "🎧 Audio"

        if obj.message_type == Message.MessageType.FILE:
            return obj.file_name or "📎 File"

        return None

    # =====================================================
    # SENDER
    # =====================================================
    def get_sender(self, obj):

        if not obj.sender:
            return None

        return obj.sender.id

    # =====================================================
    # REPLY
    # =====================================================
    def get_reply(self, obj):

        if not obj.reply_to:
            return None

        reply = obj.reply_to

        if reply.deleted:
            preview = "This message was deleted"

        elif reply.message_type == Message.MessageType.TEXT:
            preview = reply.content

        elif reply.message_type == Message.MessageType.IMAGE:
            preview = "📷 Photo"

        elif reply.message_type == Message.MessageType.VIDEO:
            preview = "🎥 Video"

        elif reply.message_type == Message.MessageType.AUDIO:
            preview = "🎧 Audio"

        else:
            preview = (
                reply.file_name or "📎 File"
            )

        return {
            "id": str(reply.id),

            "message": preview,

            "sender": reply.sender_id,

            "deleted": reply.deleted,

            "message_type": reply.message_type,
        }

    # =====================================================
    # EDITED
    # =====================================================
    def get_edited(self, obj):

        return obj.edited_at is not None

    # =====================================================
    # STATUS
    # =====================================================
    def get_status(self, obj):

        # IMPORTANT:
        # System messages do not have statuses
        if obj.message_type == Message.MessageType.SYSTEM:
            return None

        request = self.context.get("request")

        membership_id = None

        if request and hasattr(request, "membership"):
            membership_id = request.membership.id

        return MessageService.get_aggregate_status(
            obj,
            viewer_membership_id=membership_id,
        )
    
    


class DirectChatSerializer(serializers.Serializer):
    target_membership_id = serializers.IntegerField()


class SendMessageSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField()
    content = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    file = serializers.FileField(required=False)
    reply_to_id = serializers.UUIDField(required=False)

    def validate(self, data):
        file = data.get("file")
        content = data.get("content")

        if not file and not content:
            raise serializers.ValidationError("Message must have content or file")

        return data

class CreateGroupSerializer(serializers.Serializer):

    name = serializers.CharField(
        max_length=255
    )

    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )

    avatar = serializers.ImageField(
        required=False,
        allow_null=True,
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )


    
class AddMembersSerializer(serializers.Serializer):

    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )


class RemoveMemberSerializer(serializers.Serializer):

    membership_id = serializers.IntegerField()


class UpdateRoleSerializer(serializers.Serializer):

    membership_id = serializers.IntegerField()

    role = serializers.ChoiceField(
        choices=ConversationParticipant.Role.choices
    )


class UpdateGroupSerializer(serializers.Serializer):

    name = serializers.CharField(
        required=False,
        max_length=255,
    )

    avatar = serializers.FileField(
        required=False,
        allow_null=True,
        )


    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class GroupParticipantSerializer(serializers.Serializer):

    membership_id = serializers.IntegerField(
        source="membership.id"
    )

    user_id = serializers.IntegerField(
        source="membership.user.id"
    )

    name = serializers.SerializerMethodField()

    email = serializers.EmailField(
        source="membership.user.email"
    )

    role = serializers.CharField(
        source="chat_role"
    )

    def get_name(self, obj):
        return obj.membership.user.get_full_name()


class GroupResponseSerializer(serializers.ModelSerializer):

    conversation_id = serializers.UUIDField(
        source="id"
    )

    class Meta:
        model = Conversation

        fields = [
            "conversation_id",
            "name",
            "avatar",
            "description",
            "type",
        ]


class GroupDetailsSerializer(serializers.ModelSerializer):

    participants = serializers.SerializerMethodField()

    class Meta:
        model = Conversation

        fields = [
            "id",
            "name",
            "avatar",
            "description",
            "type",
            "participants",
        ]

    def get_participants(self, obj):

        participants = obj.participants.select_related(
            "membership",
            "membership__user",
        )

        return GroupParticipantSerializer(
            participants,
            many=True,
        ).data
    



class MessageReceiptUserSerializer(serializers.Serializer):

    membership_id = serializers.IntegerField()
    name = serializers.CharField()
    avatar = serializers.CharField(
        allow_null=True,
        required=False,
    )

    status = serializers.CharField()

    delivered_at = serializers.DateTimeField(
        allow_null=True,
        required=False,
    )

    read_at = serializers.DateTimeField(
        allow_null=True,
        required=False,
    )


class MessageInfoSerializer(serializers.Serializer):

    message_id = serializers.UUIDField()

    delivered_users = (
        MessageReceiptUserSerializer(
            many=True
        )
    )

    read_users = (
        MessageReceiptUserSerializer(
            many=True
        )
    )

    delivered_count = serializers.IntegerField()
    read_count = serializers.IntegerField()