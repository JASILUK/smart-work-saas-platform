import requests

from apps.calendars.integrations.google.constants import (
    GOOGLE_CALENDAR_BASE_URL,
    GOOGLE_DEFAULT_CALENDAR_ID,
    REQUEST_TIMEOUT_SECONDS,
)

from apps.calendars.integrations.google.exceptions import (
    GoogleEventCreateFailed,
    GoogleEventUpdateFailed,
    GoogleEventDeleteFailed,
    GoogleBusySlotFetchFailed,
)
from apps.calendars.services.calendar_token_service import CalendarTokenService


class GoogleCalendarService:

    # =====================================================
    # HEADERS
    # =====================================================

    @staticmethod
    def build_headers(
        *,
        account,
    ):

        token = (
            CalendarTokenService
            .ensure_valid_access_token(
                account=account,
            )
        )

        return {
            "Authorization":
                f"Bearer {token}",
            "Content-Type":
                "application/json",
        }

    # =====================================================
    # CREATE EVENT
    # =====================================================

    @classmethod
    def create_event(
        cls,
        *,
        account,
        event_data,
    ):

        url = (

            f"{GOOGLE_CALENDAR_BASE_URL}"
            f"/calendars/"
            f"{GOOGLE_DEFAULT_CALENDAR_ID}"
            f"/events"
        )

        response = requests.post(

            url,

            headers=cls.build_headers(
                account=account,
            ),

            json=event_data,

            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        if response.status_code not in (
            200,
            201,
        ):

            raise GoogleEventCreateFailed(
                response.text
            )

        return response.json()

    # =====================================================
    # UPDATE EVENT
    # =====================================================

    @classmethod
    def update_event(
        cls,
        *,
        account,
        event_id,
        event_data,
    ):

        url = (

            f"{GOOGLE_CALENDAR_BASE_URL}"
            f"/calendars/"
            f"{GOOGLE_DEFAULT_CALENDAR_ID}"
            f"/events/"
            f"{event_id}"
        )

        response = requests.put(

            url,

            headers=cls.build_headers(
                account=account,
            ),

            json=event_data,

            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:

            raise GoogleEventUpdateFailed(
                response.text
            )

        return response.json()

    # =====================================================
    # DELETE EVENT
    # =====================================================

    @classmethod
    def delete_event(
        cls,
        *,
        account,
        event_id,
    ):

        url = (

            f"{GOOGLE_CALENDAR_BASE_URL}"
            f"/calendars/"
            f"{GOOGLE_DEFAULT_CALENDAR_ID}"
            f"/events/"
            f"{event_id}"
        )

        response = requests.delete(

            url,

            headers=cls.build_headers(
                account=account,
        ),

            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        if response.status_code not in (
            200,
            204,
        ):

            raise GoogleEventDeleteFailed(
                response.text
            )

        return True

    # =====================================================
    # GET EVENT
    # =====================================================

    @classmethod
    def get_event(
        cls,
        *,
        account,
        event_id,
    ):

        url = (

            f"{GOOGLE_CALENDAR_BASE_URL}"
            f"/calendars/"
            f"{GOOGLE_DEFAULT_CALENDAR_ID}"
            f"/events/"
            f"{event_id}"
        )

        response = requests.get(

            url,

            headers=cls.build_headers(
                account=account,
        ),

            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

        return response.json()

    # =====================================================
    # FREE BUSY
    # =====================================================

    @classmethod
    def get_busy_slots(
        cls,
        *,
        account,
        start_datetime,
        end_datetime,
    ):

        url = (

            f"{GOOGLE_CALENDAR_BASE_URL}"
            f"/freeBusy"
        )

        payload = {

            "timeMin":
                start_datetime.isoformat(),

            "timeMax":
                end_datetime.isoformat(),

            "items": [

                {
                    "id":
                        GOOGLE_DEFAULT_CALENDAR_ID
                }
            ],
        }

        response = requests.post(

            url,

            headers=cls.build_headers(
                account=account,
        ),

            json=payload,

            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:

            raise GoogleBusySlotFetchFailed(
                response.text
            )

        data = response.json()

        calendars = data.get(
            "calendars",
            {},
        )

        primary = calendars.get(
            GOOGLE_DEFAULT_CALENDAR_ID,
            {},
        )

        return primary.get(
            "busy",
            [],
        )

    # =====================================================
    # VALIDATE CONNECTION
    # =====================================================

    @classmethod
    def validate_connection(
        cls,
        *,
        account,
    ):

        try:

            cls.get_busy_slots(

                account=account,

                start_datetime=(
                    account.created_at
                ),

                end_datetime=(
                    account.created_at
                ),
            )

            return True

        except Exception:

            return False