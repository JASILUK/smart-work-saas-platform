from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.calendars.models.calendar_account import (
    CalendarAccount,
)

from apps.calendars.selectors.calendar_account_selector import (
    CalendarAccountSelector,
)

from apps.calendars.integrations.factory import (
    CalendarProviderFactory,
)


class CalendarAccountService:

    # =====================================================
    # CONNECT URL
    # =====================================================

    @staticmethod
    def get_connect_url(
        *,
        membership,
        provider,
    ):

        provider_instance = (
            CalendarProviderFactory
            .get_provider(provider)
        )

        state = str(
            membership.id
        )

        return (
            provider_instance
            .build_authorization_url(
                state=state,
            )
        )

    # =====================================================
    # CONNECT ACCOUNT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def connect_account(
        *,
        membership,
        provider,
        code,
        state,
    ):

        provider_instance = (
            CalendarProviderFactory
            .get_provider(provider)
        )


        expected_state = str(
            membership.id
        )

        if state != expected_state:

            raise ValueError(
                "Invalid OAuth state."
            )
        
        tokens = (

            provider_instance
            .exchange_code_for_tokens(
                code=code,
            )
        )

        access_token = (
            tokens["access_token"]
        )

        refresh_token = (
            tokens.get(
                "refresh_token",
                "",
            )
        )

        expires_in = (
            tokens.get(
                "expires_in",
                3600,
            )
        )

        user_info = (

            provider_instance
            .get_user_info(
                access_token=access_token,
            )
        )

        account, _ = (

            CalendarAccount.objects
            .update_or_create(

                membership=membership,

                provider=provider,

                defaults={

                    "provider_account_id":
                        str(
                            user_info.get(
                                "id"
                            )
                        ),

                    "email":
                        user_info.get(
                            "email"
                        ),

                    "access_token":
                        access_token,

                    "refresh_token":
                        refresh_token,

                    "expires_at":
                        (
                            timezone.now()
                            +
                            timedelta(
                                seconds=expires_in
                            )
                        ),

                    "is_connected":
                        True,
                },
            )
        )

        return account

    # =====================================================
    # DISCONNECT ACCOUNT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def disconnect_account(
        *,
        membership,
        provider,
    ):

        account = (

            CalendarAccountSelector
            .get_account(

                membership=membership,

                provider=provider,
            )
        )

        if not account:

            return None

        provider_instance = (
            CalendarProviderFactory
            .get_provider(
                provider
            )
        )

        if account.access_token:

            provider_instance.revoke_token(
                token=account.access_token,
            )

        account.is_connected = False

        account.access_token = ""

        account.refresh_token = ""

        account.save(
            update_fields=[
                "is_connected",
                "access_token",
                "refresh_token",
                "updated_at",
            ]
        )

        return account

    # =====================================================
    # ACCOUNT STATUS
    # =====================================================

    @staticmethod
    def get_connected_accounts(
        *,
        membership,
    ):

        return (

            CalendarAccountSelector
            .get_connected_accounts(
                membership=membership,
            )
        )

    # =====================================================
    # VALIDATE ACCOUNT
    # =====================================================

    @staticmethod
    def validate_connection(
        *,
        account,
    ):

        provider_instance = (
            CalendarProviderFactory
            .get_provider(
                account.provider
            )
        )

        return (
            provider_instance
            .validate_connection(
                account=account,
            )
        )

    # =====================================================
    # REFRESH TOKEN
    # =====================================================

    @staticmethod
    @transaction.atomic
    def refresh_account_token(
        *,
        account,
    ):

        provider_instance = (
            CalendarProviderFactory
            .get_provider(
                account.provider
            )
        )

        token_data = (

            provider_instance
            .refresh_access_token(

                refresh_token=(
                    account.refresh_token
                )
            )
        )

        account.access_token = (
            token_data[
                "access_token"
            ]
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
                seconds=expires_in
            )
        )

        account.save(
            update_fields=[
                "access_token",
                "expires_at",
                "updated_at",
            ]
        )

        return account