# apps/calendars/models/calendar_event_sync.py

from django.db import models
from django.contrib.contenttypes.fields import (
    GenericForeignKey,
)
from django.contrib.contenttypes.models import (
    ContentType,
)

from apps.core.models import (
    TimeStampedModel,
)


class CalendarEventSync(
    TimeStampedModel
):

    class SyncStatus(
        models.TextChoices
    ):

        PENDING = (
            "pending",
            "Pending",
        )

        SYNCED = (
            "synced",
            "Synced",
        )

        FAILED = (
            "failed",
            "Failed",
        )

        DELETED = (
            "deleted",
            "Deleted",
        )

    # =====================================================
    # CALENDAR ACCOUNT
    # =====================================================

    calendar_account = models.ForeignKey(
        "calendars.CalendarAccount",
        on_delete=models.CASCADE,
        related_name="event_syncs",
    )

    provider = models.CharField(
        max_length=30,
    )

    # =====================================================
    # SOURCE OBJECT
    # =====================================================

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
    )

    object_id = models.PositiveBigIntegerField()

    content_object = GenericForeignKey(
        "content_type",
        "object_id",
    )

    # =====================================================
    # EXTERNAL EVENT
    # =====================================================

    external_event_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    external_calendar_id = models.CharField(
        max_length=255,
        default="primary",
    )

    # =====================================================
    # SYNC STATE
    # =====================================================

    sync_status = models.CharField(
        max_length=30,
        choices=SyncStatus.choices,
        default=SyncStatus.PENDING,
    )

    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    last_error = models.TextField(
        blank=True,
        default="",
    )

    class Meta:

        indexes = [

            models.Index(
                fields=[
                    "calendar_account",
                ]
            ),

            models.Index(
                fields=[
                    "provider",
                ]
            ),

            models.Index(
                fields=[
                    "sync_status",
                ]
            ),

            models.Index(
                fields=[
                    "content_type",
                    "object_id",
                ]
            ),

            models.Index(
                fields=[
                    "external_event_id",
                ]
            ),
        ]

        unique_together = [

            (
                "calendar_account",
                "provider",
                "external_event_id",
            ),

            (
                "calendar_account",
                "content_type",
                "object_id",
            ),
        ]

    def __str__(self):

        return (
            f"{self.provider}"
            f" - "
            f"{self.external_event_id}"
        )