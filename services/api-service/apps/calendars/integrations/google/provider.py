from apps.calendars.integrations.base import (
    BaseCalendarProvider,
)

from apps.calendars.integrations.google.oauth_service import (
    GoogleCalendarOAuthService,
)

from apps.calendars.integrations.google.calendar_service import (
    GoogleCalendarService,
)


class GoogleCalendarProvider(
    BaseCalendarProvider
):

    # =====================================================
    # OAUTH
    # =====================================================

    def build_authorization_url(
        self,
        *,
        state,
    ):

        return (
            GoogleCalendarOAuthService
            .build_authorization_url(
                state=state,
            )
        )

    def exchange_code_for_tokens(
        self,
        *,
        code,
    ):

        return (
            GoogleCalendarOAuthService
            .exchange_code_for_tokens(
                code=code,
            )
        )

    def get_user_info(
        self,
        *,
        access_token,
    ):

        return (
            GoogleCalendarOAuthService
            .get_user_info(
                access_token=access_token,
            )
        )

    def revoke_token(
        self,
        *,
        token,
    ):

        return (
            GoogleCalendarOAuthService
            .revoke_token(
                token=token,
            )
        )

    # =====================================================
    # TOKEN MANAGEMENT
    # =====================================================

    def refresh_access_token(
        self,
        *,
        refresh_token,
    ):

        return (
            GoogleCalendarOAuthService
            .refresh_access_token(
                refresh_token=refresh_token,
            )
        )

    # =====================================================
    # EVENTS
    # =====================================================

    def create_event(
        self,
        *,
        account,
        event_data,
    ):

        return (
            GoogleCalendarService
            .create_event(
                account=account,
                event_data=event_data,
            )
        )

    def update_event(
        self,
        *,
        account,
        external_event_id,
        event_data,
    ):

        return (
            GoogleCalendarService
            .update_event(
                account=account,
                event_id=external_event_id,
                event_data=event_data,
            )
        )

    def delete_event(
        self,
        *,
        account,
        external_event_id,
    ):

        return (
            GoogleCalendarService
            .delete_event(
                account=account,
                event_id=external_event_id,
            )
        )

    # # =====================================================
    # # SYNC
    # # =====================================================

    # def sync_event(
    #     self,
    #     *,
    #     account,
    #     meeting,
    # ):

    #     external_event_id = (
    #         meeting.provider_metadata.get(
    #             "google_event_id"
    #         )
    #     )

    #     event_data = (
    #         self.build_event_payload(
    #             meeting=meeting,
    #         )
    #     )

    #     if external_event_id:

    #         return self.update_event(

    #             account=account,

    #             external_event_id=(
    #                 external_event_id
    #             ),

    #             event_data=event_data,
    #         )

    #     return self.create_event(

    #         account=account,

    #         event_data=event_data,
    #     )

    # =====================================================
    # BUSY SLOTS
    # =====================================================

    def get_busy_slots(
        self,
        *,
        account,
        start_datetime,
        end_datetime,
    ):

        return (
            GoogleCalendarService
            .get_busy_slots(
                account=account,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
            )
        )

    # =====================================================
    # CONNECTION
    # =====================================================

    def validate_connection(
        self,
        *,
        account,
    ):

        return (
            GoogleCalendarOAuthService
            .validate_connection(
                account=account,
            )
        )

    # =====================================================
    # EVENT PAYLOAD
    # =====================================================

    @staticmethod
    def build_event_payload(
        *,
        meeting,
    ):

        return {

            "summary":
                meeting.title,

            "description":
                meeting.description,

            "start": {

                "dateTime":
                    meeting.scheduled_start.isoformat(),

                "timeZone":
                    meeting.timezone,
            },

            "end": {

                "dateTime":
                    meeting.scheduled_end.isoformat(),

                "timeZone":
                    meeting.timezone,
            },
        }