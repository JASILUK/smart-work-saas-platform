from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.db.models import F

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

import redis
from django.conf import settings

from apps.chat.services.MessageService import MessageCursorPagination
from apps.core.media_storage_service import upload_file
from apps.chat.models import (
    Message,
    Conversation,
    ConversationParticipant,
    MessageStatus,
)
from apps.chat.selectors import get_conversation_messages
from apps.core.exceptions import ApplicationError


redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


# =========================
# HELPERS
# =========================

def is_user_online(user_id):
    return redis_client.scard(f"user:{user_id}:connections") > 0


def resolve_message_type(mime_type, file_name):
    mime = (mime_type or "").lower()
    name = (file_name or "").lower()

    if mime.startswith("image/"):
        return "image"

    if mime.startswith("video/"):
        return "video"

    if mime.startswith("audio/"):
        return "audio"

    if (
        mime in [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/zip",
        ]
        or name.endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip"))
    ):
        return "file"

    return "file"


# =========================
# SERVICE
# =========================

class MessageService:

    # =========================
    # SEND MESSAGE
    # =========================
    @staticmethod
    @transaction.atomic
    def send_message(conversation_id, sender_membership, content=None, file=None, reply_to_id=None):

        conversation = get_object_or_404(Conversation, id=conversation_id)

        # ✅ Permission check
        if not ConversationParticipant.objects.filter(
            conversation=conversation,
            membership=sender_membership
        ).exists():
            raise ApplicationError("Not allowed")

        content = (content or "").strip()

        # =========================
        # FILE HANDLING
        # =========================
        upload_data = None
        message_type = "text"

        if file:
            upload_data = upload_file(file)

            message_type = resolve_message_type(
                upload_data.get("mime_type"),
                file.name
            )

        # =========================
        # VALIDATION
        # =========================
        if message_type == "text" and not content:
            raise ApplicationError("Text message needs content")

        if message_type != "text" and not upload_data:
            raise ApplicationError("Media message requires file")

        # =========================
        # REPLY
        # =========================
        reply_to = None
        if reply_to_id:
            reply_to = Message.objects.filter(id=reply_to_id).first()
            if reply_to and reply_to.conversation_id != conversation.id:
                raise ApplicationError("Invalid reply target")

        # =========================
        # CREATE MESSAGE
        # =========================
        message = Message.objects.create(
            conversation=conversation,
            sender=sender_membership,
            message_type=message_type,
            content=content or None,
            file_url=upload_data.get("url") if upload_data else None,
            file_name=file.name if file else None,
            file_size=upload_data.get("bytes") if upload_data else None,
            duration=upload_data.get("duration") if upload_data else None,
            mime_type=upload_data.get("mime_type") if upload_data else None,
            reply_to=reply_to,
        )

        # =========================
        # REPLY PAYLOAD
        # =========================
        reply_payload = MessageService._build_reply_payload(reply_to)

        # =========================
        # DELIVERY + STATUS
        # =========================
        MessageService._handle_delivery(message, sender_membership)

        # =========================
        # SOCKET BROADCAST
        # =========================
        MessageService._broadcast_message(message, reply_payload)

        return message

    # =========================
    # INTERNAL HELPERS
    # =========================

    @staticmethod
    def _build_reply_payload(reply_to):
        if not reply_to:
            return None

        if reply_to.deleted:
            msg = "This message was deleted"
        elif reply_to.message_type == "text":
            msg = reply_to.content
        elif reply_to.message_type == "image":
            msg = "📷 Photo"
        elif reply_to.message_type == "video":
            msg = "🎥 Video"
        elif reply_to.message_type == "audio":
            msg = "🎧 Audio"
        else:
            msg = reply_to.file_name or "📎 File"

        return {
            "id": str(reply_to.id),
            "message": msg,
            "sender": reply_to.sender_id,
            "deleted": reply_to.deleted,
            "message_type": reply_to.message_type,
        }

    @staticmethod
    def _handle_delivery(message, sender_membership):
        conversation = message.conversation
        participants = list(
            ConversationParticipant.objects.filter(
                conversation=conversation
            ).select_related("membership")
        )

        now = timezone.now()

        # UNREAD COUNT
        for p in participants:
            if p.membership_id == sender_membership.id:
                continue

            in_room = redis_client.sismember(
                f"room:{conversation.company_id}:{conversation.id}",
                p.membership_id
            )

            if not in_room:
                ConversationParticipant.objects.filter(
                    conversation=conversation,
                    membership_id=p.membership_id
                ).update(unread_count=F("unread_count") + 1)

        # STATUS
        statuses = []

        for p in participants:
            if p.membership_id == sender_membership.id:
                statuses.append(
                    MessageStatus(
                        message=message,
                        membership=p.membership,
                        status=MessageStatus.Status.READ,
                        delivered_at=now,
                        read_at=now,
                    )
                )
            else:
                statuses.append(
                    MessageStatus(
                        message=message,
                        membership=p.membership,
                        status=MessageStatus.Status.SENT,
                    )
                )

        MessageStatus.objects.bulk_create(statuses)

        # LAST MESSAGE UPDATE
        conversation.last_message = message
        conversation.save(update_fields=["last_message", "updated_at"])

    @staticmethod
    def _broadcast_message(message, reply_payload):

        channel_layer = get_channel_layer()

        conversation = message.conversation

        participants = list(
            ConversationParticipant.objects.filter(
                conversation=conversation
            ).select_related("membership")
        )

        # =====================================================
        # MAIN CHAT MESSAGE EVENT
        # =====================================================
        async_to_sync(channel_layer.group_send)(
            f"tenant_{conversation.company_id}_room_{conversation.id}",
            {
                "type": "chat_message",

                "id": str(message.id),

                "room_id": str(conversation.id),

                "message": message.content or "",

                "message_type": message.message_type,

                "file_url": message.file_url,
                "mime_type": message.mime_type,
                "file_name": message.file_name,
                "duration": message.duration,

                "sender": message.sender_id,

                "created_at": message.created_at.isoformat(),

                "status": "sent",

                "deleted": False,

                "reply": reply_payload,
            }
        )

        # =====================================================
        # DELIVERY STATUS
        # =====================================================
        now = timezone.now()

        for p in participants:

            if p.membership_id == message.sender_id:
                continue

            if is_user_online(p.membership_id):

                MessageStatus.objects.filter(
                    message=message,
                    membership=p.membership,
                ).update(
                    status=MessageStatus.Status.DELIVERED,
                    delivered_at=now,
                )

                async_to_sync(channel_layer.group_send)(
                    f"tenant_{conversation.company_id}_room_{conversation.id}",
                    {
                        "type": "status_update",

                        "room_id": str(conversation.id),

                        "message_id": str(message.id),

                        "status": MessageService.get_aggregate_status(
                            message,
                            viewer_membership_id=message.sender_id,
                        ),
                    }
                )

        # =====================================================
        # REFRESH PARTICIPANT STATES
        # =====================================================
        participant_states = {
            p.membership_id: p.unread_count
            for p in ConversationParticipant.objects.filter(
                conversation=conversation
            )
        }

        # =====================================================
        # USER PERSONAL EVENTS
        # =====================================================
        for p in participants:

            # ---------------------------------------------
            # INCOMING MESSAGE EVENT
            # ---------------------------------------------
            async_to_sync(channel_layer.group_send)(
                f"tenant_{conversation.company_id}_user_{p.membership_id}",
                {
                    "type": "incoming_message",

                    "message_id": str(message.id),

                    "room_id": str(conversation.id),
                }
            )

            # ---------------------------------------------
            # SIDEBAR UPDATE EVENT
            # ---------------------------------------------
            preview_message = ""

            if message.deleted:
                preview_message = "This message was deleted"

            elif message.message_type == "text":
                preview_message = message.content or ""

            elif message.message_type == "image":
                preview_message = "📷 Photo"

            elif message.message_type == "video":
                preview_message = "🎥 Video"

            elif message.message_type == "audio":
                preview_message = "🎧 Audio"

            else:
                preview_message = (
                    message.file_name or "📎 File"
                )

            async_to_sync(channel_layer.group_send)(
                f"tenant_{conversation.company_id}_user_{p.membership_id}",
                {
                    "type": "sidebar_update",

                    "conversation_id": str(conversation.id),

                    "last_message": preview_message,

                    "updated_at": message.created_at.isoformat(),

                    "sender": message.sender_id,

                    "unread_count": participant_states.get(
                        p.membership_id,
                        0,
                    ),
                }
            )


    # =========================
    # SYSTEM MESSAGE REALTIME
    # =========================
    @staticmethod
    def broadcast_system_message(message):

        channel_layer = get_channel_layer()

        conversation = message.conversation

        participants = list(
            ConversationParticipant.objects.filter(
                conversation=conversation
            )
        )

        # ==========================================
        # UPDATE CONVERSATION LAST MESSAGE
        # ==========================================
        conversation.last_message = message

        conversation.save(
            update_fields=[
                "last_message",
                "updated_at",
            ]
        )

        # ==========================================
        # ROOM REALTIME EVENT
        # ==========================================
        payload = {
            "type": "chat_message",

            "id": str(message.id),

            "room_id": str(conversation.id),

            "message": message.content,

            "message_type": Message.MessageType.SYSTEM,

            "system_event_type": (
                message.system_event_type
            ),

            "metadata": (
                message.metadata or {}
            ),

            "sender": None,

            "created_at": (
                message.created_at.isoformat()
            ),

            # IMPORTANT:
            # System messages have no status
            "status": None,

            "deleted": False,

            "edited": False,

            "reply": None,
        }

        async_to_sync(
            channel_layer.group_send
        )(
            (
                f"tenant_{conversation.company_id}"
                f"_room_{conversation.id}"
            ),
            payload,
        )

        # ==========================================
        # SIDEBAR UPDATE
        # ==========================================
        for participant in participants:

            async_to_sync(
                channel_layer.group_send
            )(
                (
                    f"tenant_{conversation.company_id}"
                    f"_user_{participant.membership_id}"
                ),
                {
                    "type": "sidebar_update",

                    "conversation_id": (
                        str(conversation.id)
                    ),

                    "last_message": (
                        message.content
                    ),

                    "message_type": (
                        Message.MessageType.SYSTEM
                    ),

                    "system_event_type": (
                        message.system_event_type
                    ),

                    "updated_at": (
                        message.created_at.isoformat()
                    ),

                    "sender": None,
                }
            )

            
    # =========================
    # DELETE MESSAGE
    # =========================
    @staticmethod
    @transaction.atomic
    def delete_message(message_id, membership):
        message = get_object_or_404(Message, id=message_id)

        if message.sender_id != membership.id:
            raise ApplicationError("You can only delete your own message")

        if timezone.now() - message.created_at > timedelta(minutes=15):
            raise ApplicationError("Delete time expired")

        if message.deleted:
            return message

        now = timezone.now()

        message.deleted = True
        message.deleted_at = now
        message.save(update_fields=["deleted", "deleted_at"])

        async_to_sync(get_channel_layer().group_send)(
            f"tenant_{message.conversation.company_id}_room_{message.conversation_id}",
            {
                "type": "message_deleted",
                "message_id": str(message.id),
                "room_id": str(message.conversation_id),
                "deleted_at": now.isoformat(),
            }
        )

        return message

    # =========================
    # EDIT MESSAGE
    # =========================
    @staticmethod
    @transaction.atomic
    def edit_message(message_id, membership, new_content):
        message = get_object_or_404(Message, id=message_id)

        if message.sender_id != membership.id:
            raise ApplicationError("You can only edit your own message")

        if message.message_type != Message.MessageType.TEXT:
            raise ApplicationError("Only text messages can be edited")

        if timezone.now() - message.created_at > timedelta(minutes=15):
            raise ApplicationError("Edit time expired")

        if message.content == new_content:
            return message

        message.content = new_content
        message.edited_at = timezone.now()
        message.save(update_fields=["content", "edited_at"])

        async_to_sync(get_channel_layer().group_send)(
            f"tenant_{message.conversation.company_id}_room_{message.conversation_id}",
            {
                "type": "message_edited",
                "message_id": str(message.id),
                "room_id": str(message.conversation_id),
                "content": message.content,
                "edited_at": message.edited_at.isoformat(),
            }
        )

        return message

    # =========================
    # READ RECEIPTS
    # =========================
    @staticmethod
    def mark_conversation_as_read(conversation_id, membership):

        now = timezone.now()

        # =========================
        # GET TARGET STATUSES
        # =========================
        target_statuses = list(
            MessageStatus.objects.select_related(
                "message",
                "message__conversation",
            ).filter(
                message__conversation_id=conversation_id,
                membership=membership,
                status__in=[
                    MessageStatus.Status.SENT,
                    MessageStatus.Status.DELIVERED,
                ],
            )
        )

        if not target_statuses:
            return

        # =========================
        # UPDATE
        # =========================
        MessageStatus.objects.filter(
            id__in=[s.id for s in target_statuses]
        ).update(
            status=MessageStatus.Status.READ,
            read_at=now,
        )

        # =========================
        # RESET UNREAD
        # =========================
        ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            membership=membership,
        ).update(
            unread_count=0
        )

        # =========================
        # BROADCAST AGGREGATE
        # =========================
        processed_messages = set()

        for status in target_statuses:

            message = status.message

            if message.id in processed_messages:
                continue

            processed_messages.add(message.id)

            # 🔥 refresh statuses
            message.refresh_from_db()
            message = (
                Message.objects
                .prefetch_related("statuses")
                .get(id=message.id)
            )

            MessageService.broadcast_status_update(message)

    # =========================
    # FETCH
    # =========================
    @staticmethod
    def get_paginated_messages(conversation_id, membership, cursor=None, limit=20):
        queryset = MessageService.get_messages(conversation_id, membership)

        paginator = MessageCursorPagination(
            queryset=queryset,
            cursor=cursor,
            limit=limit,
        )

        return paginator.paginate()

    @staticmethod
    def get_messages(conversation_id, membership):
        is_member = ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            membership=membership
        ).exists()

        if not is_member:
            raise ApplicationError("Not allowed")

        return get_conversation_messages(conversation_id).prefetch_related("statuses")


    @staticmethod
    def get_aggregate_status(message, viewer_membership_id=None):

        if (
            viewer_membership_id is not None
            and message.sender_id != viewer_membership_id
        ):
            return None

        statuses = [
            s for s in message.statuses.all()
            if s.membership_id != message.sender_id
        ]

        total = len(statuses)

        if total == 0:
            return MessageStatus.Status.READ

        read_count = sum(
            1 for s in statuses
            if s.status == MessageStatus.Status.READ
        )

        if read_count == total:
            return MessageStatus.Status.READ

        delivered_count = sum(
            1 for s in statuses
            if s.status in [
                MessageStatus.Status.DELIVERED,
                MessageStatus.Status.READ,
            ]
        )

        if delivered_count == total:
            return MessageStatus.Status.DELIVERED

        return MessageStatus.Status.SENT
    

    @staticmethod
    def broadcast_status_update(message):

        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            f"tenant_{message.conversation.company_id}_room_{message.conversation_id}",
            {
                "type": "status_update",
                "room_id": str(message.conversation_id),
                "message_id": str(message.id),

                # ✅ aggregate
                "status": MessageService.get_aggregate_status(
                    message,
                    viewer_membership_id=message.sender_id,
                ),
            }
        )

    


    @staticmethod
    def get_message_info(
        message_id,
        membership,
    ):

        # =====================================================
        # GET MESSAGE
        # =====================================================
        message = (
            Message.objects
            .select_related(
                "sender",
                "conversation",
            )
            .prefetch_related(
                "statuses",
                "statuses__membership",
                "statuses__membership__user",
            )
            .filter(
                id=message_id,
                deleted=False,
            )
            .first()
        )

        if not message:
            raise ApplicationError(
                "Message not found"
            )

        # =====================================================
        # ONLY SENDER CAN SEE INFO
        # =====================================================
        if message.sender_id != membership.id:
            raise ApplicationError(
                "Not allowed"
            )

        # =====================================================
        # VERIFY PARTICIPANT
        # =====================================================
        is_participant = (
            ConversationParticipant.objects.filter(
                conversation=message.conversation,
                membership=membership,
            ).exists()
        )

        if not is_participant:
            raise ApplicationError(
                "Not allowed"
            )

        delivered_users = []
        read_users = []

        # =====================================================
        # EXCLUDE SENDER STATUS
        # =====================================================
        statuses = [
            s for s in message.statuses.all()
            if s.membership_id != membership.id
        ]

        # =====================================================
        # BUILD PAYLOAD
        # =====================================================
        for status in statuses:

            member = status.membership
            user = getattr(member, "user", None)

            profile = getattr(
                user,
                "profile",
                None,
            ) if user else None

            payload = {
                "membership_id": member.id,

                "name": (
                    user.username
                    if user else "User"
                ),

                "avatar": (
                    profile.avatar.url
                    if profile and profile.avatar
                    else None
                ),

                "status": status.status,

                "delivered_at": (
                    status.delivered_at
                ),

                "read_at": (
                    status.read_at
                ),
            }

            # =====================================================
            # DELIVERED USERS
            # =====================================================
            if status.status == MessageStatus.Status.DELIVERED:
                delivered_users.append(payload)

            # =====================================================
            # READ USERS
            # =====================================================
            if status.status == MessageStatus.Status.READ:
                read_users.append(payload)

        # =====================================================
        # RESPONSE
        # =====================================================
        return {
            "message_id": message.id,

            "delivered_users": delivered_users,
            "read_users": read_users,

            "delivered_count": len(delivered_users),
            "read_count": len(read_users),

            "total_participants": (
                message.conversation.participants.count() - 1
            ),
        }