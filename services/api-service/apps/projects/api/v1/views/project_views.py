from typing import Any, Dict, Optional

from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError as DRFValidationError

from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse
from apps.core.standers_pagination import StandardLimitOffsetPagination, PaginationAdapter

from apps.projects.api.v1.serializers.project_serializer import (
    ProjectCreateSerializer,
    ProjectUpdateSerializer,
    ProjectListSerializer,
    ProjectDetailSerializer,
    ProjectArchiveSerializer,
    ProjectRestoreSerializer,
)
from apps.projects.services.project_service import ProjectService
from apps.projects.selectors.project_selector import ProjectSelector
from apps.projects.models.projects import Project


# ================================================================
# PROJECT LIST & CREATE
# ================================================================

class ProjectListCreateAPIView(BaseCompanyAPIView):
    """
    GET  /api/v1/projects/      — List visible projects with filtering, pagination, and summary.
    POST /api/v1/projects/      — Create a new project with optional initial members.
    """

    required_permissions = {
        "GET": "tenant.project.view",
        "POST": "tenant.project.create"
    }

    def get(self, request, *args, **kwargs):
        """
        List projects visible to the requesting membership.
        """
        company = request.company
        membership = request.membership

        search = request.query_params.get("search")
        status_filter = request.query_params.get("status")
        visibility = request.query_params.get("visibility")
        owner = request.query_params.get("owner")
        ordering = request.query_params.get("ordering", "-created_at")

        queryset = ProjectService.list_projects(
            company=company,
            membership=membership,
            search=search,
            status=status_filter,
            visibility=visibility,
            owner=int(owner) if owner and owner.isdigit() else None,
            ordering=ordering,
        )

        paginator = StandardLimitOffsetPagination()
        paginated_page = paginator.paginate_queryset(queryset, request)

        serializer = ProjectListSerializer(paginated_page, many=True)
        pagination = PaginationAdapter.get_metadata(paginator, paginated_page)

        filters = {
            "statuses": [
                {"value": s[0], "label": s[1]}
                for s in Project.Status.choices
            ],
            "visibility": [
                {"value": v[0], "label": v[1]}
                for v in Project.Visibility.choices
            ],
            "ordering": [
                {"value": "-created_at", "label": "Newest first"},
                {"value": "created_at", "label": "Oldest first"},
                {"value": "name", "label": "Name (A-Z)"},
                {"value": "-name", "label": "Name (Z-A)"},
                {"value": "status", "label": "Status"},
            ],
        }

        # Calculate summary scoped exclusively to projects visible to this user
        summary = ProjectSelector.get_projects_summary(company, membership)

        return ApiResponse.success(
            data={
                "results": serializer.data,
                "pagination": pagination,
                "filters": filters,
                "summary": summary,
            }
        )

    def post(self, request, *args, **kwargs):
        """
        Create a new project.
        """
        company = request.company
        membership = request.membership

        serializer = ProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Automatically default owner_id to current user if not provided in payload
        owner_id = validated_data.pop("owner_id", None) or membership.id

        create_kwargs = {
            "company": company,
            "created_by_id": membership.id,
            "owner_id": owner_id,
            **validated_data,
        }

        project = ProjectService.create_project(**create_kwargs)
        detail_serializer = ProjectDetailSerializer(project)

        return ApiResponse.success(
            data=detail_serializer.data,
            status=status.HTTP_201_CREATED,
        )


# ================================================================
# PROJECT DETAIL (OVERVIEW)
# ================================================================

class ProjectDetailAPIView(BaseCompanyAPIView):
    """
    GET /api/v1/projects/{id}/  — Retrieve complete project workspace overview.
    """

    required_permissions = {
        "GET": "tenant.project.view",
    }

    def get(self, request, project_id: int, *args, **kwargs):
        """
        Retrieve project workspace overview if visible to requesting membership.
        """
        company = request.company
        membership = request.membership

        project = ProjectService.get_project(
            project_id=project_id,
            company=company,
            membership=membership,
        )

        serializer = ProjectDetailSerializer(project)
        return ApiResponse.success(data=serializer.data)


# ================================================================
# PROJECT UPDATE
# ================================================================

class ProjectUpdateAPIView(BaseCompanyAPIView):
    """
    PATCH /api/v1/projects/{id}/  — Update project fields.
    """

    required_permissions = {
        "PATCH": "tenant.project.create"
    }

    def patch(self, request, project_id: int, *args, **kwargs):
        company = request.company
        membership = request.membership

        serializer = ProjectUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        project = ProjectService.update_project(
            project_id=project_id,
            company=company,
            membership=membership,
            **serializer.validated_data,
        )

        detail_serializer = ProjectDetailSerializer(project)
        return ApiResponse.success(data=detail_serializer.data)


# ================================================================
# PROJECT ARCHIVE
# ================================================================

class ProjectArchiveAPIView(BaseCompanyAPIView):
    """
    POST /api/v1/projects/{id}/archive/  — Archive a project.
    """

    required_permissions = {
        "POST": "tenant.project.create"
    }

    def post(self, request, project_id: int, *args, **kwargs):
        company = request.company
        membership = request.membership

        serializer = ProjectArchiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project = ProjectService.archive_project(
            project_id=project_id,
            company=company,
            membership=membership,
        )

        return ApiResponse.success(
            data={
                "id": project.id,
                "name": project.name,
                "status": project.status,
                "archived_at": project.archived_at,
                "message": "Project archived successfully.",
            }
        )


# ================================================================
# PROJECT RESTORE
# ================================================================

class ProjectRestoreAPIView(BaseCompanyAPIView):
    """
    POST /api/v1/projects/{id}/restore/  — Restore an archived project.
    """

    required_permissions = {
        "POST": "tenant.project.create"
    }

    def post(self, request, project_id: int, *args, **kwargs):
        company = request.company
        membership = request.membership

        serializer = ProjectRestoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project = ProjectService.restore_project(
            project_id=project_id,
            company=company,
            membership=membership,
        )

        return ApiResponse.success(
            data={
                "id": project.id,
                "name": project.name,
                "status": project.status,
                "archived_at": project.archived_at,
                "message": "Project restored successfully.",
            }
        )