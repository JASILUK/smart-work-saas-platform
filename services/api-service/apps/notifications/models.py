import uuid

from django.db import models

from apps.core.models import TimeStampedModel


class NotificationDevice(TimeStampedModel):

    class Platform(models.TextChoices):
        WEB = "web", "Web"
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notification_devices",
    )

    membership = models.ForeignKey(
        "companies.Membership",
        on_delete=models.CASCADE,
        related_name="notification_devices",
    )

    # =====================================================
    # DEVICE IDENTITY
    # =====================================================

    device_id = models.CharField(
        max_length=255,
    )

    # =====================================================
    # PUSH TOKEN
    # =====================================================

    token = models.TextField()

    platform = models.CharField(
        max_length=20,
        choices=Platform.choices,
    )

    device_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    last_seen_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        db_table = "notification_devices"

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "membership",
                    "device_id",
                ],
                name="unique_membership_device",
            ),
        ]

        indexes = [
            models.Index(fields=["membership"]),
            models.Index(fields=["user"]),
            models.Index(fields=["platform"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):

        return (
            f"{self.membership_id} - "
            f"{self.platform}"
        )
    


class NotificationPreference(TimeStampedModel):

    membership = models.OneToOneField(
        "companies.Membership",
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )

    # =====================================================
    # GLOBAL TOGGLES
    # =====================================================

    push_enabled = models.BooleanField(
        default=True,
    )

    sound_enabled = models.BooleanField(
        default=True,
    )

    # =====================================================
    # FEATURE TOGGLES
    # =====================================================

    chat_message_enabled = models.BooleanField(
        default=True,
    )

    mention_enabled = models.BooleanField(
        default=True,
    )

    meeting_enabled = models.BooleanField(
        default=True,
    )

    attendance_enabled = models.BooleanField(
        default=True,
    )

    system_enabled = models.BooleanField(
        default=True,
    )

    class Meta:

        db_table = (
            "notification_preferences"
        )

    def __str__(self):

        return (
            f"Preferences - "
            f"{self.membership_id}"
        )
    
# =========================================================
# DATABASE NOTIFICATION HISTORY
# =========================================================

class Notification(TimeStampedModel):

    class Type(models.TextChoices):
        CHAT = "chat", "Chat"
        MENTION = "mention", "Mention"
        SYSTEM = "system", "System"
        MEETING = "meeting", "Meeting"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    membership = models.ForeignKey(
        "companies.Membership",
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    type = models.CharField(
        max_length=30,
        choices=Type.choices,
    )

    title = models.CharField(
        max_length=255,
    )

    body = models.TextField()

    data = models.JSONField(
        default=dict,
        blank=True,
    )

    is_read = models.BooleanField(
        default=False,
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:

        db_table = "notifications"

        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["membership"]),
            models.Index(fields=["type"]),
            models.Index(fields=["is_read"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.title