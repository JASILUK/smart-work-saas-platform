from apps.meetings.models.session import (
    MeetingSession,
)

from apps.meetings.integrations.rtc.livekit.provider import (
    LiveKitRTCProvider,
)


class RTCProviderFactory:

    # =====================================================
    # GET PROVIDER
    # =====================================================

    @staticmethod
    def get_provider(
        provider_name,
    ):

        providers = {

            MeetingSession
            .RTCProvider
            .LIVEKIT:

            LiveKitRTCProvider,
        }

        provider_class = providers.get(
            provider_name
        )

        if not provider_class:

            raise ValueError(
                "Unsupported RTC provider."
            )

        return provider_class()