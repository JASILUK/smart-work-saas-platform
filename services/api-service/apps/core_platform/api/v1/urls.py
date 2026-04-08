from django.urls import path

from apps.core_platform.api.v1.views.permission_Views import (
    PlatformContextAPI,
    PlatformPermissionDetailAPI,
    PlatformPermissionListCreateAPI,
)
from apps.core_platform.api.v1.views.platform_role_view import (
    PlatformRoleDetailAPI,
    PlatformRoleListCreateAPI,
)

urlpatterns = [
    path("context/", PlatformContextAPI.as_view(), name="platform-context-api"),
    path(
        "permissions/",
        PlatformPermissionListCreateAPI.as_view(),
        name="platfrom-permissions",
    ),
    path(
        "permissions/<int:pk>/",
        PlatformPermissionDetailAPI.as_view(),
        name="permission-detailed-api",
    ),
    path("roles/", PlatformRoleListCreateAPI.as_view(), name="platform-roles"),
    path(
        "roles/<int:pk>/", PlatformRoleDetailAPI.as_view(), name="roles-deatiled-view"
    ),
]
