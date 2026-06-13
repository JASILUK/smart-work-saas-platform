from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.calendars.integrations.google.oauth_service import (
    GoogleCalendarOAuthService,
)


class CalendarTokenService:

    REFRESH_BUFFER_MINUTES = 5

    @classmethod
    def ensure_valid_access_token(
        cls,
        *,
        account,
    ):

        if not cls.is_expired(account=account):

            return account.access_token

        return cls.refresh_account_token(
            account=account,
        )

    @classmethod
    def is_expired(
        cls,
        *,
        account,
    ):

        if not account.expires_at:

            return True

        return (

            account.expires_at

            <=

            timezone.now()
            +
            timedelta(
                minutes=cls.REFRESH_BUFFER_MINUTES
            )
        )

    @classmethod
    @transaction.atomic
    def refresh_account_token(
        cls,
        *,
        account,
    ):

        token_data = (
            GoogleCalendarOAuthService
            .refresh_access_token(
                refresh_token=
                    account.refresh_token,
            )
        )

        account.access_token = (
            token_data["access_token"]
        )

        expires_in = (
            token_data.get(
                "expires_in",
                3600,
            )
        )

        account.expires_at = (

            timezone.now()

            +

            timedelta(
                seconds=expires_in,
            )
        )

        account.save(
            update_fields=[
                "access_token",
                "expires_at",
                "updated_at",
            ]
        )

        return account.access_token