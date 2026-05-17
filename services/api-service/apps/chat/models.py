import uuid

from django.db import models

from apps.core.models import TimeStampedModel


class Conversation(TimeStampedModel):

    class Type(models.TextChoices):
        DIRECT = "direct", "Direct"
        GROUP = "group", "Group"
        DEPARTMENT = "department", "Department"
        PROJECT = "project", "Project"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="conversations",
    )

    type = models.CharField(
        max_length=20,
        choices=Type.choices,
    )

    name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    avatar = models.URLField(
        null=True,
        blank=True,
    )

    description = models.TextField(
        null=True,
        blank=True,
    )

    # =====================================================
    # SYSTEM MANAGED CONVERSATION
    # =====================================================

    is_system_managed = models.BooleanField(
        default=False,
    )

    created_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_conversations",
    )

    last_message = models.ForeignKey(
        "chat.Message",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:

        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["type"]),
            models.Index(fields=["updated_at"]),
            models.Index(fields=["is_system_managed"]),
        ]

    def __str__(self):

        return (
            self.name
            or str(self.id)
        )


class ConversationParticipant(TimeStampedModel):

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="participants",
    )

    membership = models.ForeignKey(
        "companies.Membership",
        on_delete=models.CASCADE,
        related_name="chat_memberships",
    )

    chat_role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )

    unread_count = models.PositiveIntegerField(
        default=0,
    )

    is_muted = models.BooleanField(
        default=False,
    )

    is_pinned = models.BooleanField(
        default=False,
    )

    last_read_message = models.ForeignKey(
        "chat.Message",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:

        unique_together = [
            ("conversation", "membership"),
        ]

        indexes = [
            models.Index(fields=["conversation"]),
            models.Index(fields=["membership"]),
            models.Index(fields=["chat_role"]),
        ]

    def __str__(self):

        return (
            f"{self.membership_id} - "
            f"{self.conversation_id}"
        )


class Message(TimeStampedModel):

    class MessageType(models.TextChoices):
        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        AUDIO = "audio", "Audio"
        FILE = "file", "File"
        SYSTEM = "system", "System"

    class SystemEventType(models.TextChoices):
        GROUP_CREATED = "group_created", "Group Created"
        MEMBER_ADDED = "member_added", "Member Added"
        MEMBER_REMOVED = "member_removed", "Member Removed"
        MEMBER_LEFT = "member_left", "Member Left"
        ROLE_UPDATED = "role_updated", "Role Updated"
        GROUP_UPDATED = "group_updated", "Group Updated"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender = models.ForeignKey(
        "companies.Membership",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )

    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT,
    )

    system_event_type = models.CharField(
        max_length=50,
        choices=SystemEventType.choices,
        null=True,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    mime_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )

    content = models.TextField(
        null=True,
        blank=True,
    )

    file_url = models.URLField(
        null=True,
        blank=True,
    )

    file_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    reply_to = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replies",
    )

    edited_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    deleted = models.BooleanField(
        default=False,
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:

        indexes = [
            models.Index(
                fields=[
                    "conversation",
                    "created_at",
                ]
            ),
            models.Index(fields=["sender"]),
            models.Index(fields=["message_type"]),
        ]

    def __str__(self):

        return str(self.id)


class MessageStatus(TimeStampedModel):

    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        READ = "read", "Read"

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="statuses",
    )

    membership = models.ForeignKey(
        "companies.Membership",
        on_delete=models.CASCADE,
        related_name="message_statuses",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SENT,
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:

        unique_together = [
            ("message", "membership"),
        ]

        indexes = [
            models.Index(
                fields=[
                    "message",
                    "membership",
                ]
            ),
            models.Index(
                fields=[
                    "membership",
                    "status",
                ]
            ),
        ]

    def __str__(self):

        return (
            f"{self.message_id} - "
            f"{self.membership_id}"
        )