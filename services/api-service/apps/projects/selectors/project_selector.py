from typing import Any, Dict, Optional
from django.db.models import (
    QuerySet,
    Q,
    Exists,
    OuterRef,
    Count,
    Case,
    When,
    Value,
    IntegerField,
)
from django.db.models.functions import Coalesce

from apps.projects.models.projects import Project
from apps.projects.models.project_members import ProjectMember
from apps.projects.selectors.project_member_selector import ProjectMemberSelector


class ProjectSelector:
    """
    Read-only data access layer for Project models.

    Enforces multi-tenant scoping and visibility rules.
    All database reads for the projects module flow through here.
    """

    # ------------------------------------------------------------------
    # Base QuerySet
    # ------------------------------------------------------------------

    @classmethod
    def _base_qs(cls) -> QuerySet[Project]:
        """
        Base queryset with common select_related optimizations.
        """
        return Project.objects.select_related(
            "company",
            "owner",
            "owner__user",
            "created_by",
            "created_by__user",
            "updated_by",
            "updated_by__user",
        )

    # ------------------------------------------------------------------
    # Existence Checks
    # ------------------------------------------------------------------

    @classmethod
    def exists_code(
        cls,
        company=None,
        code: str = "",
        exclude_project_id: Optional[int] = None,
        company_id: Optional[int] = None,
    ) -> bool:
        """
        Check if a project code already exists within a company.
        Supports passing either `company` instance or `company_id` kwarg.
        """
        target_company = company if company is not None else company_id
        qs = Project.objects.filter(company=target_company, code__iexact=code)

        if exclude_project_id is not None:
            qs = qs.exclude(id=exclude_project_id)

        return qs.exists()

    # ------------------------------------------------------------------
    # Single Object Fetch
    # ------------------------------------------------------------------

    @classmethod
    def get_by_id(
        cls,
        company=None,
        project_id: Optional[int] = None,
        company_id: Optional[int] = None,
    ) -> Optional[Project]:
        """
        Fetch a single project by ID scoped to a company.
        Supports passing either `company` instance or `company_id` kwarg.
        """
        target_company = company if company is not None else company_id
        try:
            return (
                cls._base_qs()
                .filter(company=target_company, id=project_id)
                .first()
            )
        except Project.DoesNotExist:
            return None

    # ------------------------------------------------------------------
    # Visibility-Aware Fetch
    # ------------------------------------------------------------------

    @classmethod
    def get_visible_project(
        cls,
        company,
        membership,
        project_id: int,
    ) -> Optional[Project]:
        """
        Fetch a project only if the membership is allowed to view it.
        Annotates member statistics directly in single SQL query.
        """
        is_member = Exists(
            ProjectMember.objects.filter(
                project=OuterRef("pk"),
                membership=membership,
            )
        )

        try:
            return (
                cls._base_qs()
                .filter(
                    company=company,
                    id=project_id,
                )
                .annotate(
                    _is_member=is_member,
                    total_members=Coalesce(Count("memberships", distinct=True), 0),
                    owner_count=Coalesce(
                        Count(
                            Case(
                                When(memberships__role=ProjectMember.Role.OWNER, then=1)
                            ),
                            distinct=True,
                        ),
                        0,
                    ),
                    manager_count=Coalesce(
                        Count(
                            Case(
                                When(memberships__role=ProjectMember.Role.MANAGER, then=1)
                            ),
                            distinct=True,
                        ),
                        0,
                    ),
                    member_role_count=Coalesce(
                        Count(
                            Case(
                                When(memberships__role=ProjectMember.Role.MEMBER, then=1)
                            ),
                            distinct=True,
                        ),
                        0,
                    ),
                )
                .filter(
                    Q(visibility=Project.Visibility.PUBLIC) | Q(_is_member=True)
                )
                .first()
            )
        except Project.DoesNotExist:
            return None

    # ------------------------------------------------------------------
    # Visibility-Aware List
    # ------------------------------------------------------------------

    @classmethod
    def get_visible_projects(
        cls,
        company,
        membership,
    ) -> QuerySet[Project]:
        """
        Return all projects visible to a membership within a company.
        """
        is_member = Exists(
            ProjectMember.objects.filter(
                project=OuterRef("pk"),
                membership=membership,
            )
        )

        return (
            cls._base_qs()
            .filter(company=company)
            .annotate(_is_member=is_member)
            .filter(
                Q(visibility=Project.Visibility.PUBLIC) | Q(_is_member=True)
            )
            .distinct()
            .order_by("-created_at")
        )

    # ------------------------------------------------------------------
    # Company-Scoped Lists (No Visibility Filter)
    # ------------------------------------------------------------------

    @classmethod
    def get_company_projects(
        cls,
        company,
    ) -> QuerySet[Project]:
        """
        Return all projects belonging to a company.
        """
        return (
            cls._base_qs()
            .filter(company=company)
            .order_by("-created_at")
        )

    @classmethod
    def get_archived_projects(
        cls,
        company,
    ) -> QuerySet[Project]:
        """
        Return all archived projects for a company.
        """
        return (
            cls._base_qs()
            .filter(company=company, status=Project.Status.ARCHIVED)
            .order_by("-archived_at")
        )

    @classmethod
    def get_active_projects(
        cls,
        company,
    ) -> QuerySet[Project]:
        """
        Return all non-archived projects for a company.
        """
        return (
            cls._base_qs()
            .filter(
                company=company,
                status__in=[
                    Project.Status.PLANNING,
                    Project.Status.ACTIVE,
                    Project.Status.ON_HOLD,
                    Project.Status.COMPLETED,
                ],
            )
            .order_by("-created_at")
        )

    # ------------------------------------------------------------------
    # Membership-Role Lists
    # ------------------------------------------------------------------

    @classmethod
    def get_owned_projects(
        cls,
        membership,
    ) -> QuerySet[Project]:
        """
        Return all projects where the membership is the owner.
        """
        return (
            cls._base_qs()
            .filter(owner=membership)
            .order_by("-created_at")
        )

    @classmethod
    def get_managed_projects(
        cls,
        membership,
    ) -> QuerySet[Project]:
        """
        Return all projects where the membership is a Project Manager.
        """
        return (
            cls._base_qs()
            .filter(
                memberships__membership=membership,
                memberships__role=ProjectMember.Role.MANAGER,
            )
            .distinct()
            .order_by("-created_at")
        )

    @classmethod
    def get_member_projects(
        cls,
        membership,
    ) -> QuerySet[Project]:
        """
        Return all projects where the membership is a Project Member.
        """
        return (
            cls._base_qs()
            .filter(memberships__membership=membership)
            .distinct()
            .order_by("-created_at")
        )

    # ------------------------------------------------------------------
    # Search & Filter with Annotations
    # ------------------------------------------------------------------

    @classmethod
    def search_projects(
        cls,
        company,
        membership,
        search: Optional[str] = None,
        status: Optional[str] = None,
        visibility: Optional[str] = None,
        owner: Optional[int] = None,
        ordering: Optional[str] = None,
    ) -> QuerySet[Project]:
        """
        Search, filter, and annotate projects visible to a membership.
        """
        qs = cls.get_visible_projects(company=company, membership=membership)

        qs = qs.annotate(
            member_count=Coalesce(Count("memberships", distinct=True), 0),
            task_count=Value(0, output_field=IntegerField()),
            completed_task_count=Value(0, output_field=IntegerField()),
            progress_percentage=Value(0, output_field=IntegerField()),
        )

        if search:
            search_lower = search.lower()
            qs = qs.filter(
                Q(name__icontains=search_lower)
                | Q(code__icontains=search_lower)
                | Q(client_company__icontains=search_lower)
                | Q(client_name__icontains=search_lower)
            )

        if status:
            qs = qs.filter(status=status)

        if visibility:
            qs = qs.filter(visibility=visibility)

        if owner is not None:
            qs = qs.filter(owner_id=owner)

        if ordering:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by("-created_at")

        return qs

    # ------------------------------------------------------------------
    # Summary Builders & Extension Points
    # ------------------------------------------------------------------

    @classmethod
    def get_my_membership_summary(
        cls,
        project: Project,
        membership,
    ) -> Optional[Dict[str, Any]]:
        """
        Return a summary of the current user's membership in the given project.

        Reuses ProjectMemberSelector to avoid duplicate queries.
        Returns None if the user is not a member of the project.
        """
        member = ProjectMemberSelector.get_project_member(
            project_id=project.id,
            membership_id=membership.id,
        )

        if member is None:
            return None

        return {
            "membership_id": member.membership_id,
            "role": member.role,
            "is_owner": member.is_owner,
            "is_manager": member.is_manager,
            "can_manage_members": member.can_manage_members,
        }

    @classmethod
    def get_member_summary(cls, project: Project) -> Dict[str, int]:
        return {
            "total_members": getattr(project, "total_members", 0),
            "owners": getattr(project, "owner_count", 0),
            "managers": getattr(project, "manager_count", 0),
            "members": getattr(project, "member_role_count", 0),
        }

    @classmethod
    def get_task_summary(cls, project: Project) -> Dict[str, Any]:
        return {
            "total": 0,
            "todo": 0,
            "in_progress": 0,
            "review": 0,
            "completed": 0,
            "overdue": 0,
            "progress_percentage": 0,
        }

    @classmethod
    def get_meeting_summary(cls, project: Project) -> Dict[str, int]:
        return {
            "total": 0,
            "scheduled": 0,
            "live": 0,
            "completed": 0,
        }

    @classmethod
    def get_file_summary(cls, project: Project) -> Dict[str, int]:
        return {
            "total_files": 0,
            "total_size": 0,
        }

    @classmethod
    def get_activity_summary(cls, project: Project) -> Dict[str, list]:
        return {
            "recent_events": [],
        }

    @classmethod
    def get_projects_summary(cls, company, membership=None) -> Dict[str, int]:
        """
        Calculate user-scoped project metric summaries in a SINGLE SQL query.
        If membership is passed, counts only projects visible/accessible to that user.
        """
        if membership is not None:
            visible_qs = cls.get_visible_projects(company=company, membership=membership)
        else:
            visible_qs = Project.objects.filter(company=company)

        summary_data = visible_qs.aggregate(
            total_projects=Count("id"),
            planning_projects=Count(
                Case(When(status=Project.Status.PLANNING, then=1))
            ),
            active_projects=Count(
                Case(When(status=Project.Status.ACTIVE, then=1))
            ),
            on_hold_projects=Count(
                Case(When(status=Project.Status.ON_HOLD, then=1))
            ),
            completed_projects=Count(
                Case(When(status=Project.Status.COMPLETED, then=1))
            ),
            archived_projects=Count(
                Case(When(status=Project.Status.ARCHIVED, then=1))
            ),
            public_projects=Count(
                Case(When(visibility=Project.Visibility.PUBLIC, then=1))
            ),
            private_projects=Count(
                Case(When(visibility=Project.Visibility.PRIVATE, then=1))
            ),
        )

        return {
            "total_projects": summary_data["total_projects"] or 0,
            "planning_projects": summary_data["planning_projects"] or 0,
            "active_projects": summary_data["active_projects"] or 0,
            "on_hold_projects": summary_data["on_hold_projects"] or 0,
            "completed_projects": summary_data["completed_projects"] or 0,
            "archived_projects": summary_data["archived_projects"] or 0,
            "public_projects": summary_data["public_projects"] or 0,
            "private_projects": summary_data["private_projects"] or 0,
        }

    # Legacy count helper compatibility wrappers
    @classmethod
    def count_projects(cls, company) -> int:
        return Project.objects.filter(company=company).count()

    @classmethod
    def count_active(cls, company) -> int:
        return Project.objects.filter(
            company=company,
            status__in=[
                Project.Status.PLANNING,
                Project.Status.ACTIVE,
                Project.Status.ON_HOLD,
                Project.Status.COMPLETED,
            ],
        ).count()

    @classmethod
    def count_completed(cls, company) -> int:
        return Project.objects.filter(
            company=company,
            status=Project.Status.COMPLETED,
        ).count()

    @classmethod
    def count_archived(cls, company) -> int:
        return Project.objects.filter(
            company=company,
            status=Project.Status.ARCHIVED,
        ).count()