from typing import Optional, Dict, Any
from django.db.models import QuerySet, Q, Case, When, Value, IntegerField, Count

from apps.projects.models.project_members import ProjectMember


class ProjectMemberSelector:
    """
    Read-only data access layer for ProjectMember models.

    The single gateway for all ProjectMember queries.
    Enforces project-level scoping. Optimized for enterprise APIs.
    """

    @classmethod
    def _base_qs(cls) -> QuerySet[ProjectMember]:
        return ProjectMember.objects.select_related(
            "project",
            "project__company",
            "membership",
            "membership__user",
            "added_by",
        )

    @classmethod
    def _role_order_annotation(cls):
        return Case(
            When(role=ProjectMember.Role.OWNER, then=Value(0)),
            When(role=ProjectMember.Role.MANAGER, then=Value(1)),
            When(role=ProjectMember.Role.MEMBER, then=Value(2)),
            output_field=IntegerField(),
        )

    @classmethod
    def exists(
        cls,
        project_id: int,
        membership_id: int,
    ) -> bool:
        return ProjectMember.objects.filter(
            project_id=project_id,
            membership_id=membership_id,
        ).exists()

    @classmethod
    def get_by_id(
        cls,
        member_id: int,
    ) -> Optional[ProjectMember]:
        return cls._base_qs().filter(id=member_id).first()

    @classmethod
    def get_project_member(
        cls,
        project_id: int,
        membership_id: int,
    ) -> Optional[ProjectMember]:
        return (
            cls._base_qs()
            .filter(project_id=project_id, membership_id=membership_id)
            .first()
        )

    @classmethod
    def get_project_member_by_membership(
        cls,
        project_id: int,
        membership_id: int,
    ) -> Optional[ProjectMember]:
        return cls.get_project_member(
            project_id=project_id,
            membership_id=membership_id,
        )

    @classmethod
    def get_project_members(
        cls,
        project_id: int,
    ) -> QuerySet[ProjectMember]:
        return (
            cls._base_qs()
            .filter(project_id=project_id)
            .annotate(role_order=cls._role_order_annotation())
            .order_by("role_order", "-joined_at")
        )

    @classmethod
    def get_project_owners(
        cls,
        project_id: int,
    ) -> QuerySet[ProjectMember]:
        return (
            cls._base_qs()
            .filter(project_id=project_id, role=ProjectMember.Role.OWNER)
        )

    @classmethod
    def get_project_managers(
        cls,
        project_id: int,
    ) -> QuerySet[ProjectMember]:
        return (
            cls._base_qs()
            .filter(project_id=project_id, role=ProjectMember.Role.MANAGER)
            .order_by("-joined_at")
        )

    @classmethod
    def get_regular_members(
        cls,
        project_id: int,
    ) -> QuerySet[ProjectMember]:
        return (
            cls._base_qs()
            .filter(project_id=project_id, role=ProjectMember.Role.MEMBER)
            .order_by("-joined_at")
        )

    @classmethod
    def is_project_member(
        cls,
        project_id: int,
        membership_id: int,
    ) -> bool:
        return ProjectMember.objects.filter(
            project_id=project_id,
            membership_id=membership_id,
        ).exists()

    @classmethod
    def is_owner(
        cls,
        project_id: int,
        membership_id: int,
    ) -> bool:
        return ProjectMember.objects.filter(
            project_id=project_id,
            membership_id=membership_id,
            role=ProjectMember.Role.OWNER,
        ).exists()

    @classmethod
    def is_manager(
        cls,
        project_id: int,
        membership_id: int,
    ) -> bool:
        return ProjectMember.objects.filter(
            project_id=project_id,
            membership_id=membership_id,
            role=ProjectMember.Role.MANAGER,
        ).exists()

    @classmethod
    def can_manage_members(
        cls,
        project_id: int,
        membership_id: int,
    ) -> bool:
        return ProjectMember.objects.filter(
            project_id=project_id,
            membership_id=membership_id,
            role__in=[
                ProjectMember.Role.OWNER,
                ProjectMember.Role.MANAGER,
            ],
        ).exists()

    @classmethod
    def count_members(
        cls,
        project_id: int,
    ) -> int:
        return ProjectMember.objects.filter(project_id=project_id).count()

    @classmethod
    def count_members_by_role(
        cls,
        project_id: int,
    ) -> Dict[str, int]:
        counts = (
            ProjectMember.objects.filter(project_id=project_id)
            .values("role")
            .annotate(count=Count("id"))
        )

        result = {
            "owners": 0,
            "managers": 0,
            "members": 0,
            "total": 0,
        }

        for item in counts:
            role = item["role"]
            count = item["count"]
            result[role + "s"] = count
            result["total"] += count

        return result

    @classmethod
    def search_members(
        cls,
        project_id: int,
        search: Optional[str] = None,
        role: Optional[str] = None,
        ordering: Optional[str] = None,
    ) -> QuerySet[ProjectMember]:
        qs = cls._base_qs().filter(project_id=project_id)

        if role:
            qs = qs.filter(role=role)

        if search:
            search_lower = search.lower()
            qs = qs.filter(
                Q(membership__user__first_name__icontains=search_lower)
                | Q(membership__user__last_name__icontains=search_lower)
                | Q(membership__user__email__icontains=search_lower)
            )

        if ordering:
            qs = qs.order_by(ordering)
        else:
            qs = qs.annotate(role_order=cls._role_order_annotation())
            qs = qs.order_by("role_order", "-joined_at")

        return qs