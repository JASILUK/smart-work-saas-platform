# =========================================================
# BASE
# =========================================================

class GoogleCalendarError(
    Exception
):
    """
    Base Google Calendar exception.
    """

    pass


# =========================================================
# OAUTH
# =========================================================

class GoogleOAuthError(
    GoogleCalendarError
):
    """
    OAuth related errors.
    """

    pass


class GoogleAuthorizationFailed(
    GoogleOAuthError
):
    """
    User denied authorization
    or authorization failed.
    """

    pass


class GoogleTokenExchangeFailed(
    GoogleOAuthError
):
    """
    Failed to exchange code
    for tokens.
    """

    pass


class GoogleTokenRefreshFailed(
    GoogleOAuthError
):
    """
    Failed to refresh token.
    """

    pass


class GoogleTokenRevocationFailed(
    GoogleOAuthError
):
    """
    Failed to revoke token.
    """

    pass


class GoogleUserInfoFetchFailed(
    GoogleOAuthError
):
    """
    Failed to retrieve user profile.
    """

    pass


# =========================================================
# CALENDAR
# =========================================================

class GoogleCalendarApiError(
    GoogleCalendarError
):
    """
    Generic Google Calendar API error.
    """

    pass


class GoogleEventCreateFailed(
    GoogleCalendarApiError
):
    """
    Failed to create event.
    """

    pass


class GoogleEventUpdateFailed(
    GoogleCalendarApiError
):
    """
    Failed to update event.
    """

    pass


class GoogleEventDeleteFailed(
    GoogleCalendarApiError
):
    """
    Failed to delete event.
    """

    pass


class GoogleBusySlotFetchFailed(
    GoogleCalendarApiError
):
    """
    Failed to fetch availability data.
    """

    pass


# =========================================================
# CONNECTION
# =========================================================

class GoogleConnectionInvalid(
    GoogleCalendarError
):
    """
    Stored account connection
    is no longer valid.
    """

    pass


class GoogleAccountNotConnected(
    GoogleCalendarError
):
    """
    Calendar account is not connected.
    """

    pass