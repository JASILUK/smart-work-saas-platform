import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class Conversation(TimeStampedModel):

    class Type(models.TextChoices):
        DIRECT = "direct", "Direct"
        GROUP = "group", "Group"
        DEPARTMENT = "department", "Department"
        PROJECT = "project", "Project"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="conversations"
    )

    type = models.CharField(max_length=20, choices=Type.choices)

    name = models.CharField(max_length=255, blank=True, null=True)

    department = models.ForeignKey(
        "companies.Department",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="department_chats"
    )

    created_by = models.ForeignKey(
        "users.User",
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_conversations"
    )

    last_message = models.ForeignKey(
        "chat.Message",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+"
    )

    class Meta:
        indexes = [
            models.Index(fields=["company"]),
            models.Index(fields=["type"]),
            models.Index(fields=["updated_at"]),  # 🔥 IMPORTANT
        ]


class ConversationParticipant(TimeStampedModel):

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="participants"
    )

    membership = models.ForeignKey(
        "companies.Membership",
        on_delete=models.CASCADE,
        related_name="chat_memberships"
    )

    chat_role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER
    )

    unread_count = models.IntegerField(default=0)

    class Meta:
        unique_together = ("conversation", "membership")
        indexes = [
            models.Index(fields=["membership"]),
        ]


class Message(TimeStampedModel):

    class MessageType(models.TextChoices):
        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        FILE = "file", "File"
        SYSTEM = "system", "System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    sender = models.ForeignKey(
        "companies.Membership",
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )

    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT
    )

    content = models.TextField(blank=True)

    file = models.FileField(upload_to="chat_files/", null=True, blank=True)

    edited_at = models.DateTimeField(null=True, blank=True)

    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]


class MessageStatus(TimeStampedModel):

    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        READ = "read", "Read"

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="statuses"
    )

    membership = models.ForeignKey(
        "companies.Membership",
        on_delete=models.CASCADE
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SENT
    )

    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("message", "membership")
        indexes = [
            models.Index(fields=["message", "membership"]),
            models.Index(fields=["membership", "status"]),  # 🔥 CRITICAL
        ]