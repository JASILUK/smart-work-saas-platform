from apps.calendars.models.calendar_account import (
    CalendarAccount,
)


class CalendarAccountSelector:

    # =====================================================
    # CONNECTED ACCOUNTS
    # =====================================================

    @staticmethod
    def get_connected_accounts(
        *,
        membership,
    ):

        accounts = (

            CalendarAccount.objects

            .filter(
                membership=membership,
                is_connected=True,
            )

            .order_by("provider")
        )

        result = {

            "google": {
                "connected": False,
                "email": None,
            },

            "outlook": {
                "connected": False,
                "email": None,
            },
        }

        for account in accounts:

            result[
                account.provider
            ] = {

                "connected": True,

                "email": account.email,
            }

        return result

    # =====================================================
    # GET ACCOUNT
    # =====================================================

    @staticmethod
    def get_account(
        *,
        membership,
        provider,
    ):

        return (

            CalendarAccount.objects

            .filter(
                membership=membership,
                provider=provider,
                is_connected=True,
            )

            .first()
        )

    # =====================================================
    # GET ACCOUNT BY ID
    # =====================================================

    @staticmethod
    def get_account_by_id(
        *,
        account_id,
    ):

        return (

            CalendarAccount.objects

            .filter(
                id=account_id,
            )

            .first()
        )

    # =====================================================
    # HAS ACCOUNT
    # =====================================================

    @staticmethod
    def has_connected_account(
        *,
        membership,
        provider,
    ):

        return (

            CalendarAccount.objects

            .filter(
                membership=membership,
                provider=provider,
                is_connected=True,
            )

            .exists()
        )

    # =====================================================
    # ALL ACCOUNTS
    # =====================================================

    @staticmethod
    def get_accounts(
        *,
        membership,
    ):

        return (

            CalendarAccount.objects

            .filter(
                membership=membership,
                is_connected=True,
            )

            .order_by("provider")
        )

    # =====================================================
    # PROVIDER ACCOUNT
    # =====================================================

    @staticmethod
    def get_provider_account(
        *,
        provider,
        provider_account_id,
    ):

        return (

            CalendarAccount.objects

            .filter(
                provider=provider,
                provider_account_id=provider_account_id,
            )

            .first()
        )