from abc import ABC
from abc import abstractmethod


class BaseCalendarProvider(
    ABC
):

    # =====================================================
    # OAUTH
    # =====================================================

    @abstractmethod
    def build_authorization_url(
        self,
        *,
        state,
    ):
        """
        Return provider authorization URL.
        """
        raise NotImplementedError

    @abstractmethod
    def exchange_code_for_tokens(
        self,
        *,
        code,
    ):
        """
        Exchange OAuth authorization code
        for access and refresh tokens.
        """
        raise NotImplementedError

    @abstractmethod
    def get_user_info(
        self,
        *,
        access_token,
    ):
        """
        Return provider account details.
        Example:
        {
            "id": "...",
            "email": "..."
        }
        """
        raise NotImplementedError

    @abstractmethod
    def revoke_token(
        self,
        *,
        token,
    ):
        """
        Disconnect calendar account.
        """
        raise NotImplementedError

    # =====================================================
    # TOKEN MANAGEMENT
    # =====================================================

    @abstractmethod
    def refresh_access_token(
        self,
        *,
        refresh_token,
    ):
        """
        Generate a new access token
        using refresh token.
        """
        raise NotImplementedError

    # =====================================================
    # CALENDAR EVENTS
    # =====================================================

    @abstractmethod
    def create_event(
        self,
        *,
        account,
        meeting,
    ):
        """
        Create provider calendar event.
        """
        raise NotImplementedError

    @abstractmethod
    def update_event(
        self,
        *,
        account,
        meeting,
        external_event_id,
    ):
        """
        Update existing provider event.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_event(
        self,
        *,
        account,
        external_event_id,
    ):
        """
        Delete provider event.
        """
        raise NotImplementedError

    
    # =====================================================
    # AVAILABILITY
    # =====================================================

    @abstractmethod
    def get_busy_slots(
        self,
        *,
        account,
        start_datetime,
        end_datetime,
    ):
        """
        Return busy slots from provider.
        Used for scheduling validation.
        """
        raise NotImplementedError

    # =====================================================
    # HEALTH CHECK
    # =====================================================

    @abstractmethod
    def validate_connection(
        self,
        *,
        account,
    ):
        """
        Verify account connection
        is still valid.
        """
        raise NotImplementedError