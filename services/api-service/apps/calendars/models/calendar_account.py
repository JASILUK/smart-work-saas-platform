from django.db import models

from apps.core.models import (
    TimeStampedModel,
)


class CalendarAccount(
    TimeStampedModel
):

    class Provider(
        models.TextChoices
    ):

        GOOGLE = (
            "google",
            "Google",
        )

        OUTLOOK = (
            "outlook",
            "Outlook",
        )

    membership = models.ForeignKey(
        "companies.Membership",
        on_delete=models.CASCADE,
        related_name="calendar_accounts",
    )

    provider = models.CharField(
        max_length=30,
        choices=Provider.choices,
    )

    provider_account_id = models.CharField(
        max_length=255,
        db_index=True,
    )

    email = models.EmailField()

    access_token = models.TextField()

    refresh_token = models.TextField()

    expires_at = models.DateTimeField()

    is_connected = models.BooleanField(
        default=True,
    )

    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:

        unique_together = [

            (
                "membership",
                "provider",
            ),
        ]

        indexes = [

            models.Index(
                fields=[
                    "membership",
                ],
            ),

            models.Index(
                fields=[
                    "provider",
                ],
            ),
        ]