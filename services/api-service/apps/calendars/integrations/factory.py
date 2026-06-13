from apps.calendars.models.calendar_account import (
    CalendarAccount,
)

from apps.calendars.integrations.google.provider import (
    GoogleCalendarProvider,
)


class CalendarProviderFactory:

    # =====================================================
    # PROVIDERS
    # =====================================================

    PROVIDERS = {

        CalendarAccount.Provider.GOOGLE:
            GoogleCalendarProvider,

        # Future

        # CalendarAccount.Provider.OUTLOOK:
        #     OutlookCalendarProvider,
    }

    # =====================================================
    # GET PROVIDER
    # =====================================================

    @classmethod
    def get_provider(
        cls,
        provider,
    ):

        provider_class = (
            cls.PROVIDERS.get(
                provider
            )
        )

        if not provider_class:

            raise ValueError(
                (
                    "Unsupported calendar "
                    f"provider: {provider}"
                )
            )

        return provider_class()

    # =====================================================
    # GET FROM ACCOUNT
    # =====================================================

    @classmethod
    def get_provider_for_account(
        cls,
        *,
        account,
    ):

        return cls.get_provider(
            account.provider
        )

    # =====================================================
    # SUPPORTED
    # =====================================================

    @classmethod
    def is_supported(
        cls,
        provider,
    ):

        return (
            provider
            in
            cls.PROVIDERS
        )

    # =====================================================
    # LIST SUPPORTED
    # =====================================================

    @classmethod
    def supported_providers(
        cls,
    ):

        return list(
            cls.PROVIDERS.keys()
        )