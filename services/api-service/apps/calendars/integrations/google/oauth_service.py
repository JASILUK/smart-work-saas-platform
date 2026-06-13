import requests

from urllib.parse import urlencode

from django.conf import settings
from django.utils import timezone

from apps.calendars.integrations.google.constants import (
    GOOGLE_AUTH_URL,
    GOOGLE_TOKEN_URL,
    GOOGLE_REVOKE_URL,
    GOOGLE_USER_INFO_URL,
    GOOGLE_SCOPES,
    REQUEST_TIMEOUT_SECONDS,
)

from apps.calendars.integrations.google.exceptions import (
    GoogleAuthorizationFailed,
    GoogleTokenExchangeFailed,
    GoogleTokenRefreshFailed,
    GoogleTokenRevocationFailed,
    GoogleUserInfoFetchFailed,
    GoogleConnectionInvalid,
)


class GoogleCalendarOAuthService:

    # =====================================================
    # AUTHORIZE URL
    # =====================================================

    @classmethod
    def build_authorization_url(
        cls,
        *,
        state,
    ):

        query = {

            "client_id":
                settings.GOOGLE_CLIENT_ID,

            "redirect_uri":
                settings.GOOGLE_CALENDAR_REDIRECT_URI,

            "response_type":
                "code",

            "access_type":
                "offline",

            "prompt":
                "consent",

            "scope":
                " ".join(
                    GOOGLE_SCOPES
                ),

            "state":
                state,
        }

        return (
            f"{GOOGLE_AUTH_URL}?"
            f"{urlencode(query)}"
        )

    # =====================================================
    # EXCHANGE CODE
    # =====================================================

    @classmethod
    def exchange_code_for_tokens(
        cls,
        *,
        code,
    ):

        response = requests.post(

            GOOGLE_TOKEN_URL,

            data={

                "client_id":
                    settings.GOOGLE_CLIENT_ID,

                "client_secret":
                    settings.GOOGLE_CLIENT_SECRET,

                "redirect_uri":
                    settings.GOOGLE_CALENDAR_REDIRECT_URI,

                "grant_type":
                    "authorization_code",

                "code":
                    code,
            },

            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:

            raise GoogleTokenExchangeFailed(
                response.text
            )

        return response.json()

    # =====================================================
    # REFRESH TOKEN
    # =====================================================

    @classmethod
    def refresh_access_token(
        cls,
        *,
        refresh_token,
    ):

        response = requests.post(

            GOOGLE_TOKEN_URL,

            data={

                "client_id":
                    settings.GOOGLE_CLIENT_ID,

                "client_secret":
                    settings.GOOGLE_CLIENT_SECRET,

                "refresh_token":
                    refresh_token,

                "grant_type":
                    "refresh_token",
            },

            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:

            raise GoogleTokenRefreshFailed(
                response.text
            )

        return response.json()

    # =====================================================
    # USER INFO
    # =====================================================

    @classmethod
    def get_user_info(
        cls,
        *,
        access_token,
    ):

        response = requests.get(

            GOOGLE_USER_INFO_URL,

            headers={
                "Authorization":
                    f"Bearer {access_token}"
            },

            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        if response.status_code != 200:

            raise GoogleUserInfoFetchFailed(
                response.text
            )

        return response.json()

    # =====================================================
    # REVOKE TOKEN
    # =====================================================

    @classmethod
    def revoke_token(
        cls,
        *,
        token,
    ):

        response = requests.post(

            GOOGLE_REVOKE_URL,

            params={
                "token": token,
            },

            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        if response.status_code not in (
            200,
            400,
        ):

            raise GoogleTokenRevocationFailed(
                response.text
            )

        return True

    # =====================================================
    # TOKEN VALIDATION
    # =====================================================

    @classmethod
    def validate_access_token(
        cls,
        *,
        access_token,
    ):

        try:

            cls.get_user_info(
                access_token=access_token,
            )

            return True

        except Exception:

            return False

    # =====================================================
    # CONNECTION CHECK
    # =====================================================

    @classmethod
    def validate_connection(
        cls,
        *,
        account,
    ):

        if not account.is_connected:

            raise GoogleConnectionInvalid(
                "Account disconnected."
            )

        is_valid = (
            cls.validate_access_token(
                access_token=account.access_token,
            )
        )

        if is_valid:

            return True

        refreshed = (
            cls.refresh_access_token(
                refresh_token=account.refresh_token,
            )
        )

        account.access_token = (
            refreshed["access_token"]
        )

        expires_in = (
            refreshed.get(
                "expires_in",
                3600,
            )
        )

        account.expires_at = (
            timezone.now()
            +
            timezone.timedelta(
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

        return True