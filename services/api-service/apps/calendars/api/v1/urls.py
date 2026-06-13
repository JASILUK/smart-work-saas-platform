from django.urls import path

from apps.calendars.api.v1.views import (
    CalendarAccountsView,
    CalendarConnectUrlView,
    CalendarOAuthCallbackView,
    CalendarDisconnectView,
)

urlpatterns = [

    # =====================================================
    # CALENDAR ACCOUNTS
    # =====================================================

    path(
        "accounts/",
        CalendarAccountsView.as_view(),
        name="calendar-accounts",
    ),

    # =====================================================
    # CONNECT URL
    # =====================================================

    path(
        "connect-url/",
        CalendarConnectUrlView.as_view(),
        name="calendar-connect-url",
    ),

    # =====================================================
    # OAUTH CALLBACK
    # =====================================================

    path(
        "callback/",
        CalendarOAuthCallbackView.as_view(),
        name="calendar-oauth-callback",
    ),

    # =====================================================
    # DISCONNECT
    # =====================================================

    path(
        "disconnect/",
        CalendarDisconnectView.as_view(),
        name="calendar-disconnect",
    ),
]