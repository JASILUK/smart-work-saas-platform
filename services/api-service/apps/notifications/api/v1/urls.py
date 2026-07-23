from django.urls import path

from apps.notifications.api.v1.views.notification_view import (
    NotificationDeviceListView,
    RegisterDeviceView,
    DeactivateDeviceView,
    NotificationPreferenceView,
    )

from apps.notifications.api.v1.views.app_notification_view import (
        NotificationListView,
        NotificationUnreadCountView,
        NotificationReadAllView,
        NotificationClearReadView,
        NotificationReadView,
        NotificationDetailView,
    
    )

urlpatterns = [

    # Device & Preference Endpoints
    path(
        "devices/register/",
        RegisterDeviceView.as_view(),
        name="register-device",
    ),

    path(
        "devices/deactivate/",
        DeactivateDeviceView.as_view(),
        name="deactivate-device",
    ),

    path(
        "preferences/",
        NotificationPreferenceView.as_view(),
        name="notification-preferences",
    ),

    path(
        "devices/",
        NotificationDeviceListView.as_view(),
        name="notification-devices",
    ),

    # Notification Center Endpoints
    path(
        "",
        NotificationListView.as_view(),
        name="notification-list",
    ),

    path(
        "unread-count/",
        NotificationUnreadCountView.as_view(),
        name="notification-unread-count",
    ),

    path(
        "read-all/",
        NotificationReadAllView.as_view(),
        name="notification-read-all",
    ),

    path(
        "read/",
        NotificationClearReadView.as_view(),
        name="notification-clear-read",
    ),

    path(
        "<uuid:notification_id>/read/",
        NotificationReadView.as_view(),
        name="notification-mark-read",
    ),

    path(
        "<uuid:notification_id>/",
        NotificationDetailView.as_view(),
        name="notification-detail",
    ),
]