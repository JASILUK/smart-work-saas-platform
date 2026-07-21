from typing import Any, Dict, Optional
from rest_framework import status

from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse
from apps.core.standers_pagination import StandardLimitOffsetPagination, PaginationAdapter

from apps.projects.api.v1.serializers.project_member_serializers import (
    ProjectMemberListSerializer,
    ProjectMemberDetailSerializer,
    ProjectMemberCreateSerializer,
    ProjectMemberBulkCreateSerializer,
    ProjectMemberUpdateSerializer,
    ProjectMemberTransferOwnershipSerializer,
    ProjectMemberRemoveSerializer,
)
from apps.projects.services.project_member_service import ProjectMemberService
from apps.projects.selectors.project_member_selector import ProjectMemberSelector
from apps.projects.models.project_members import ProjectMember


# ================================================================
# PROJECT MEMBER LIST & CREATE
# ================================================================

class ProjectMemberListCreateAPIView(BaseCompanyAPIView):
    """
    GET  /api/v1/projects/{project_id}/members/  — List project members.
    POST /api/v1/projects/{project_id}/members/  — Add a single member.
    """

    required_permissions = {
        "GET": "tenant.project.view",
        "POST": "tenant.project.view",  # Delegated to ProjectMemberValidator
    }

    # ---- GET: List ----
    def get(self, request, project_id: int, *args, **kwargs):
        company = request.company
        membership = request.membership

        search = request.query_params.get("search")
        role = request.query_params.get("role")
        ordering = request.query_params.get("ordering")

        queryset = ProjectMemberService.list_members(
            project_id=project_id,
            company_id=company.id,
            membership=membership,
            search=search,
            role=role,
            ordering=ordering,
        )

        paginator = StandardLimitOffsetPagination()
        paginated_page = paginator.paginate_queryset(queryset, request)

        serializer = ProjectMemberListSerializer(paginated_page, many=True)
        pagination = PaginationAdapter.adapt(paginator, request)

        filters = {
            "roles": [
                {"value": r[0], "label": r[1]}
                for r in ProjectMember.Role.choices
            ],
            "ordering": [
                {"value": "", "label": "Role hierarchy (default)"},
                {"value": "-joined_at", "label": "Newest first"},
                {"value": "joined_at", "label": "Oldest first"},
                {"value": "membership__user__first_name", "label": "Name (A-Z)"},
            ],
        }

        counts = ProjectMemberSelector.count_members_by_role(project_id=project_id)
        summary = {
            "total_members": counts["total"],
            "owners": counts["owners"],
            "managers": counts["managers"],
            "members": counts["members"],
        }

        return ApiResponse.success(
            data={
                "results": serializer.data,
                "pagination": pagination,
                "filters": filters,
                "summary": summary,
            }
        )

    # ---- POST: Create ----
    def post(self, request, project_id: int, *args, **kwargs):
        company = request.company
        membership = request.membership

        serializer = ProjectMemberCreateSerializer(
            data=request.data,
            context={
                "project_id": project_id,
                "company": company,
                "actor_membership_id": membership.id,
            },
        )
        serializer.is_valid(raise_exception=True)

        member = serializer.save()

        detail_serializer = ProjectMemberDetailSerializer(member)
        return ApiResponse.success(
            data=detail_serializer.data,
            status=status.HTTP_201_CREATED,
        )


# ================================================================
# PROJECT MEMBER DETAIL
# ================================================================

class ProjectMemberDetailAPIView(BaseCompanyAPIView):
    """
    GET /api/v1/projects/{project_id}/members/{member_id}/  — Member detail.
    """

    required_permissions = {
        "GET": "tenant.project.view",
    }

    def get(self, request, project_id: int, member_id: int, *args, **kwargs):
        member = ProjectMemberSelector.get_by_id(member_id=member_id)

        if not member or member.project_id != project_id:
            return ApiResponse.error(
                message="Member not found.",
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProjectMemberDetailSerializer(member)
        return ApiResponse.success(data=serializer.data)


# ================================================================
# PROJECT MEMBER UPDATE
# ================================================================

class ProjectMemberUpdateAPIView(BaseCompanyAPIView):
    """
    PATCH /api/v1/projects/{project_id}/members/{member_id}/  — Update member.
    """

    required_permissions = {
        "PATCH": "tenant.project.view",  # Delegated to ProjectMemberValidator
    }

    def patch(self, request, project_id: int, member_id: int, *args, **kwargs):
        company = request.company
        membership = request.membership

        member = ProjectMemberSelector.get_by_id(member_id=member_id)
        if not member or member.project_id != project_id:
            return ApiResponse.error(
                message="Member not found.",
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProjectMemberUpdateSerializer(
            instance=member,
            data=request.data,
            partial=True,
            context={
                "project_id": project_id,
                "company": company,
                "actor_membership_id": membership.id,
            },
        )
        serializer.is_valid(raise_exception=True)

        updated_member = serializer.save()

        detail_serializer = ProjectMemberDetailSerializer(updated_member)
        return ApiResponse.success(data=detail_serializer.data)


# ================================================================
# PROJECT MEMBER REMOVE
# ================================================================

class ProjectMemberRemoveAPIView(BaseCompanyAPIView):
    """
    DELETE /api/v1/projects/{project_id}/members/{member_id}/  — Remove member.
    """

    required_permissions = {
        "DELETE": "tenant.project.view",  # Delegated to ProjectMemberValidator
    }

    def delete(self, request, project_id: int, member_id: int, *args, **kwargs):
        company = request.company
        membership = request.membership

        member = ProjectMemberSelector.get_by_id(member_id=member_id)
        if not member or member.project_id != project_id:
            return ApiResponse.error(
                message="Member not found.",
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProjectMemberRemoveSerializer(
            context={
                "project_id": project_id,
                "company": company,
                "actor_membership_id": membership.id,
            },
        )
        deleted_info = serializer.delete(instance=member)

        return ApiResponse.success(
            data={
                "id": deleted_info["id"],
                "membership_id": deleted_info["membership_id"],
                "message": "Project member removed successfully.",
            }
        )


# ================================================================
# PROJECT OWNERSHIP TRANSFER
# ================================================================

class ProjectTransferOwnershipAPIView(BaseCompanyAPIView):
    """
    POST /api/v1/projects/{project_id}/members/transfer-owner/
    — Transfer project ownership.
    """

    required_permissions = {
        "POST": "tenant.project.view",  # Delegated to ProjectMemberValidator
    }

    def post(self, request, project_id: int, *args, **kwargs):
        company = request.company
        membership = request.membership

        serializer = ProjectMemberTransferOwnershipSerializer(
            data=request.data,
            context={
                "project_id": project_id,
                "company": company,
                "actor_membership_id": membership.id,
            },
        )
        serializer.is_valid(raise_exception=True)

        result = serializer.save()

        return ApiResponse.success(
            data={
                "project_id": result["project"]["id"],
                "old_owner": result["old_owner"],
                "new_owner": result["new_owner"],
                "message": "Project ownership transferred successfully.",
            }
        )