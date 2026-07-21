# apps/projects/api/v1/urls.py

from django.urls import path, include

from apps.projects.api.v1.views.project_views import (
    ProjectListCreateAPIView,
    ProjectDetailAPIView,
    ProjectUpdateAPIView,
    ProjectArchiveAPIView,
    ProjectRestoreAPIView,
)
from apps.projects.api.v1.views.project_member_views import (
    ProjectMemberListCreateAPIView,
    ProjectMemberDetailAPIView,
    ProjectMemberUpdateAPIView,
    ProjectMemberRemoveAPIView,
    ProjectTransferOwnershipAPIView,
)


app_name = "projects_v1"

# Project member URLs (nested under project)
project_member_patterns = [
    # List & Create member
    path(
        "members/",
        ProjectMemberListCreateAPIView.as_view(),
        name="project-member-list-create",
    ),
    # Transfer ownership
    path(
        "members/transfer-owner/",
        ProjectTransferOwnershipAPIView.as_view(),
        name="project-transfer-ownership",
    ),
    # Member detail
    path(
        "members/<int:member_id>/",
        ProjectMemberDetailAPIView.as_view(),
        name="project-member-detail",
    ),
    # Update member
    path(
        "members/<int:member_id>/update/",
        ProjectMemberUpdateAPIView.as_view(),
        name="project-member-update",
    ),
    # Remove member
    path(
        "members/<int:member_id>/remove/",
        ProjectMemberRemoveAPIView.as_view(),
        name="project-member-remove",
    ),
]

# Main project URLs
urlpatterns = [
    # List & Create
    path(
        "",
        ProjectListCreateAPIView.as_view(),
        name="project-list-create",
    ),
    # Detail
    path(
        "<int:project_id>/",
        ProjectDetailAPIView.as_view(),
        name="project-detail",
    ),
    # Update
    path(
        "<int:project_id>/update/",
        ProjectUpdateAPIView.as_view(),
        name="project-update",
    ),
    # Archive
    path(
        "<int:project_id>/archive/",
        ProjectArchiveAPIView.as_view(),
        name="project-archive",
    ),
    # Restore
    path(
        "<int:project_id>/restore/",
        ProjectRestoreAPIView.as_view(),
        name="project-restore",
    ),
    # Nested member URLs
    path(
        "<int:project_id>/",
        include(project_member_patterns),
    ),
]

