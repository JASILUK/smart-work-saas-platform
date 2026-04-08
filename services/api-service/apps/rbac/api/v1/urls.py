from django.urls import path

from apps.rbac.api.v1.views import RoleDetailAPI, RoleListCreateAPI, TenantPermissionListAPI

urlpatterns = [
    path("roles/", RoleListCreateAPI.as_view(), name="company-roles"),
    path("roles/<int:pk>/", RoleDetailAPI.as_view(), name="company-roles-deatiled-api"),
    path("permissions/", TenantPermissionListAPI.as_view(), name="tenant-permissions"),
]
