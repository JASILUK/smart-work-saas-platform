from django.urls import path

from apps.notifications.api.v1.views import (
    NotificationDeviceListView,
    RegisterDeviceView,
    DeactivateDeviceView,
    NotificationPreferenceView,
)

urlpatterns = [

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
]