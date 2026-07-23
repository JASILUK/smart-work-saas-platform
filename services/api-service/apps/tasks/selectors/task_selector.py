from datetime import date
from typing import Any, Dict, List, Optional, Tuple, Union

from django.db import models
from django.db.models import (
    Case,
    Count,
    F,
    IntegerField,
    Q,
    QuerySet,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.companies.models import Company, Membership
from apps.projects.models.project_members import ProjectMember
from apps.projects.models.projects import Project
from apps.projects.selectors.project_selector import ProjectSelector
from apps.tasks.models.tasks import Task, TaskPriority, TaskStatus


class TaskSelector:
    """
    Read-only Query Engine for the Task domain model.

    Enforces multi-tenant company isolation, prevents N+1 queries via
    optimized select_related joins, reuses existing ProjectSelector rules,
    and provides composable query methods for personal, project, team, and
    company-wide tasks.
    """

    # =========================================================================
    # BASE OPTIMIZED QUERYSET
    # =========================================================================

    @classmethod
    def _base_qs(cls) -> QuerySet[Task]:
        """
        Foundation QuerySet enforcing zero N+1 lookups across relations.
        Executes a single SQL JOIN pass for nested user, project, and department data.
        """
        return Task.objects.select_related(
            "company",
            "project",
            "project__company",
            "created_by",
            "created_by__user",
            "created_by__department",
            "assigned_to",
            "assigned_to__user",
            "assigned_to__department",
        )

    # =========================================================================
    # COMPOSABLE FILTER ENGINE
    # =========================================================================

    @classmethod
    def _apply_filters(
        cls,
        qs: QuerySet[Task],
        *,
        search: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        project_id: Optional[int] = None,
        assigned_to_id: Optional[int] = None,
        created_by_id: Optional[int] = None,
        department_id: Optional[int] = None,
        is_personal: Optional[bool] = None,
        is_overdue: Optional[bool] = None,
        is_today: Optional[bool] = None,
        is_this_week: Optional[bool] = None,
        start_date_range: Optional[Tuple[Optional[date], Optional[date]]] = None,
        due_date_range: Optional[Tuple[Optional[date], Optional[date]]] = None,
        ordering: Optional[str] = None,
        **kwargs,
    ) -> QuerySet[Task]:
        """
        Internal composable filter engine that modifies QuerySets without evaluation.
        """
        today = timezone.localdate()

        # ---------------------------------------------------------------------
        # 1. Text Search (Title & Description)
        # ---------------------------------------------------------------------
        if search:
            search_str = search.strip().lower()
            qs = qs.filter(
                Q(title__icontains=search_str)
                | Q(description__icontains=search_str)
            )

        # ---------------------------------------------------------------------
        # 2. Exact Field Lookups
        # ---------------------------------------------------------------------
        if status:
            qs = qs.filter(status=status)

        if priority:
            qs = qs.filter(priority=priority)

        if project_id is not None:
            qs = qs.filter(project_id=project_id)

        if assigned_to_id is not None:
            qs = qs.filter(assigned_to_id=assigned_to_id)

        if created_by_id is not None:
            qs = qs.filter(created_by_id=created_by_id)

        if department_id is not None:
            qs = qs.filter(
                Q(assigned_to__department_id=department_id)
                | Q(created_by__department_id=department_id)
            )

        # ---------------------------------------------------------------------
        # 3. Scope Discriminator (Personal vs Project Tasks)
        # ---------------------------------------------------------------------
        if is_personal is True:
            qs = qs.filter(project__isnull=True)
        elif is_personal is False:
            qs = qs.filter(project__isnull=False)

        # ---------------------------------------------------------------------
        # 4. Date & Deadline Convenience Filters
        # ---------------------------------------------------------------------
        if is_overdue is True:
            qs = qs.filter(
                due_date__lt=today,
                status__in=[
                    TaskStatus.TODO,
                    TaskStatus.IN_PROGRESS,
                    TaskStatus.IN_REVIEW,
                ],
            )

        if is_today is True:
            qs = qs.filter(due_date=today)

        if is_this_week is True:
            start_of_week = today - timezone.timedelta(days=today.weekday())
            end_of_week = start_of_week + timezone.timedelta(days=6)
            qs = qs.filter(due_date__range=(start_of_week, end_of_week))

        if start_date_range:
            start_from, start_to = start_date_range
            if start_from:
                qs = qs.filter(start_date__gte=start_from)
            if start_to:
                qs = qs.filter(start_date__lte=start_to)

        if due_date_range:
            due_from, due_to = due_date_range
            if due_from:
                qs = qs.filter(due_date__gte=due_from)
            if due_to:
                qs = qs.filter(due_date__lte=due_to)

        # ---------------------------------------------------------------------
        # 5. Ordering Engine
        # ---------------------------------------------------------------------
        if ordering:
            ordering_map = {
                "newest": "-created_at",
                "oldest": "created_at",
                "due_date": "due_date",
                "-due_date": "-due_date",
                "priority": "priority",
                "status": "status",
                "title": "title",
                "-title": "-title",
            }
            sort_field = ordering_map.get(ordering, ordering)
            qs = qs.order_by(sort_field)
        else:
            qs = qs.order_by("-created_at")

        return qs

    # =========================================================================
    # EXISTENCE & SINGLE OBJECT SELECTORS
    # =========================================================================

    @classmethod
    def exists(
        cls,
        *,
        company: Union[Company, int],
        task_id: int,
        project_id: Optional[int] = None,
    ) -> bool:
        """
        Check if a task exists within a specific company and optional project scope.
        """
        company_id = company.id if isinstance(company, Company) else company
        qs = Task.objects.filter(company_id=company_id, id=task_id)

        if project_id is not None:
            qs = qs.filter(project_id=project_id)

        return qs.exists()

    @classmethod
    def get_by_id(
        cls,
        *,
        company: Union[Company, int],
        task_id: int,
        project_id: Optional[int] = None,
    ) -> Optional[Task]:
        """
        Fetch a single task instance with all foreign key relations pre-fetched.
        """
        company_id = company.id if isinstance(company, Company) else company
        qs = cls._base_qs().filter(company_id=company_id, id=task_id)

        if project_id is not None:
            qs = qs.filter(project_id=project_id)

        return qs.first()

    # =========================================================================
    # COMPANY / GLOBAL SELECTORS
    # =========================================================================

    @classmethod
    def get_company_tasks(
        cls,
        *,
        company: Union[Company, int],
        search: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        project_id: Optional[int] = None,
        assigned_to_id: Optional[int] = None,
        created_by_id: Optional[int] = None,
        department_id: Optional[int] = None,
        is_personal: Optional[bool] = None,
        is_overdue: Optional[bool] = None,
        is_today: Optional[bool] = None,
        is_this_week: Optional[bool] = None,
        ordering: Optional[str] = None,
        **kwargs,
    ) -> QuerySet[Task]:
        """
        Return company-wide tasks for administrators and high-level dashboards.
        """
        company_id = company.id if isinstance(company, Company) else company
        qs = cls._base_qs().filter(company_id=company_id)

        return cls._apply_filters(
            qs,
            search=search,
            status=status,
            priority=priority,
            project_id=project_id,
            assigned_to_id=assigned_to_id,
            created_by_id=created_by_id,
            department_id=department_id,
            is_personal=is_personal,
            is_overdue=is_overdue,
            is_today=is_today,
            is_this_week=is_this_week,
            ordering=ordering,
            **kwargs,
        )

    # =========================================================================
    # PROJECT TASK SELECTORS
    # =========================================================================

    @classmethod
    def get_project_tasks(
        cls,
        *,
        company: Union[Company, int],
        project_id: int,
        search: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to_id: Optional[int] = None,
        created_by_id: Optional[int] = None,
        is_overdue: Optional[bool] = None,
        is_today: Optional[bool] = None,
        is_this_week: Optional[bool] = None,
        ordering: Optional[str] = None,
        **kwargs,
    ) -> QuerySet[Task]:
        """
        Query tasks belonging exclusively to a specific project.
        """
        company_id = company.id if isinstance(company, Company) else company
        qs = cls._base_qs().filter(company_id=company_id, project_id=project_id)

        return cls._apply_filters(
            qs,
            search=search,
            status=status,
            priority=priority,
            assigned_to_id=assigned_to_id,
            created_by_id=created_by_id,
            is_overdue=is_overdue,
            is_today=is_today,
            is_this_week=is_this_week,
            ordering=ordering,
            **kwargs,
        )

    # =========================================================================
    # MY TASKS (USER WORKSPACE SELECTORS)
    # =========================================================================

    @classmethod
    def get_my_tasks(
        cls,
        *,
        company: Union[Company, int],
        membership: Union[Membership, int],
        search: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        project_id: Optional[int] = None,
        department_id: Optional[int] = None,
        is_personal: Optional[bool] = None,
        is_overdue: Optional[bool] = None,
        is_today: Optional[bool] = None,
        is_this_week: Optional[bool] = None,
        ordering: Optional[str] = None,
        **kwargs,
    ) -> QuerySet[Task]:
        """
        Query tasks where the current membership is assigned OR creator.
        Supports filtering by project_id and department_id.
        """
        company_id = company.id if isinstance(company, Company) else company
        m_id = membership.id if isinstance(membership, Membership) else membership

        qs = cls._base_qs().filter(
            company_id=company_id,
        ).filter(
            Q(assigned_to_id=m_id) | Q(created_by_id=m_id)
        )

        return cls._apply_filters(
            qs,
            search=search,
            status=status,
            priority=priority,
            project_id=project_id,
            department_id=department_id,
            is_personal=is_personal,
            is_overdue=is_overdue,
            is_today=is_today,
            is_this_week=is_this_week,
            ordering=ordering,
            **kwargs,
        )

    @classmethod
    def get_assigned_to_me(
        cls,
        *,
        company: Union[Company, int],
        membership: Union[Membership, int],
        search: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        project_id: Optional[int] = None,
        is_overdue: Optional[bool] = None,
        is_today: Optional[bool] = None,
        ordering: Optional[str] = None,
        **kwargs,
    ) -> QuerySet[Task]:
        """
        Query tasks assigned explicitly to the current membership.
        """
        company_id = company.id if isinstance(company, Company) else company
        m_id = membership.id if isinstance(membership, Membership) else membership

        qs = cls._base_qs().filter(company_id=company_id, assigned_to_id=m_id)

        return cls._apply_filters(
            qs,
            search=search,
            status=status,
            priority=priority,
            project_id=project_id,
            is_overdue=is_overdue,
            is_today=is_today,
            ordering=ordering,
            **kwargs,
        )

    @classmethod
    def get_created_by_me(
        cls,
        *,
        company: Union[Company, int],
        membership: Union[Membership, int],
        search: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        project_id: Optional[int] = None,
        ordering: Optional[str] = None,
        **kwargs,
    ) -> QuerySet[Task]:
        """
        Query tasks created explicitly by the current membership.
        """
        company_id = company.id if isinstance(company, Company) else company
        m_id = membership.id if isinstance(membership, Membership) else membership

        qs = cls._base_qs().filter(company_id=company_id, created_by_id=m_id)

        return cls._apply_filters(
            qs,
            search=search,
            status=status,
            priority=priority,
            project_id=project_id,
            ordering=ordering,
            **kwargs,
        )

    @classmethod
    def get_personal_tasks(
        cls,
        *,
        company: Union[Company, int],
        membership: Union[Membership, int],
        search: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        ordering: Optional[str] = None,
        **kwargs,
    ) -> QuerySet[Task]:
        """
        Query personal tasks (`project IS NULL`) owned by the current membership.
        """
        company_id = company.id if isinstance(company, Company) else company
        m_id = membership.id if isinstance(membership, Membership) else membership

        qs = cls._base_qs().filter(
            company_id=company_id,
            created_by_id=m_id,
            project__isnull=True,
        )

        return cls._apply_filters(
            qs,
            search=search,
            status=status,
            priority=priority,
            ordering=ordering,
            **kwargs,
        )

    # =========================================================================
    # TEAM & MANAGER HELPERS & SELECTORS
    # =========================================================================

    @classmethod
    def get_managed_project_ids(
        cls,
        *,
        membership: Union[Membership, int],
    ) -> QuerySet:
        """
        Helper selector returning IDs of all projects owned or managed by the user.
        Uses a unified Q-filter to avoid combining distinct and non-distinct QuerySets.
        """
        m_id = membership.id if isinstance(membership, Membership) else membership

        return Project.objects.filter(
            Q(owner_id=m_id)
            | Q(memberships__membership_id=m_id, memberships__role=ProjectMember.Role.MANAGER)
        ).values_list("id", flat=True).distinct()

    @classmethod
    def get_managed_team_tasks(
        cls,
        *,
        company: Union[Company, int],
        membership: Union[Membership, int],
        search: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        project_id: Optional[int] = None,
        assigned_to_id: Optional[int] = None,
        is_overdue: Optional[bool] = None,
        is_today: Optional[bool] = None,
        ordering: Optional[str] = None,
        **kwargs,
    ) -> QuerySet[Task]:
        """
        Query tasks across all projects owned or managed by the requesting user.
        """
        company_id = company.id if isinstance(company, Company) else company
        managed_pids = cls.get_managed_project_ids(membership=membership)

        qs = cls._base_qs().filter(
            company_id=company_id,
            project_id__in=managed_pids,
        )

        return cls._apply_filters(
            qs,
            search=search,
            status=status,
            priority=priority,
            project_id=project_id,
            assigned_to_id=assigned_to_id,
            is_overdue=is_overdue,
            is_today=is_today,
            ordering=ordering,
            **kwargs,
        )

    # =========================================================================
    # METRICS & AGGREGATION SUMMARY ENGINE
    # =========================================================================

    @classmethod
    def get_task_metrics_summary(
        cls,
        *,
        company: Union[Company, int],
        project_id: Optional[int] = None,
        membership_id: Optional[int] = None,
        is_personal_only: bool = False,
        is_managed_team_only: bool = False,
        requesting_membership: Optional[Union[Membership, int]] = None,
    ) -> Dict[str, int]:
        """
        Calculate complete task metric counts using a SINGLE SQL aggregate pass.
        Avoids evaluating model instances or executing loops in Python.
        """
        today = timezone.localdate()
        company_id = company.id if isinstance(company, Company) else company

        qs = Task.objects.filter(company_id=company_id)

        # Apply context constraints
        if project_id is not None:
            qs = qs.filter(project_id=project_id)

        if membership_id is not None:
            qs = qs.filter(
                Q(assigned_to_id=membership_id) | Q(created_by_id=membership_id)
            )

        if is_personal_only:
            qs = qs.filter(project__isnull=True)

        if is_managed_team_only and requesting_membership is not None:
            managed_pids = cls.get_managed_project_ids(membership=requesting_membership)
            qs = qs.filter(project_id__in=managed_pids)

        # Executed as a single SQL query via PostgreSQL conditional aggregation
        metrics = qs.aggregate(
            total=Count("id"),
            todo=Count(Case(When(status=TaskStatus.TODO, then=1))),
            in_progress=Count(Case(When(status=TaskStatus.IN_PROGRESS, then=1))),
            in_review=Count(Case(When(status=TaskStatus.IN_REVIEW, then=1))),
            completed=Count(Case(When(status=TaskStatus.COMPLETED, then=1))),
            cancelled=Count(Case(When(status=TaskStatus.CANCELLED, then=1))),
            high_priority=Count(
                Case(
                    When(
                        priority__in=[TaskPriority.HIGH, TaskPriority.CRITICAL],
                        then=1,
                    )
                )
            ),
            critical_priority=Count(
                Case(When(priority=TaskPriority.CRITICAL, then=1))
            ),
            overdue=Count(
                Case(
                    When(
                        due_date__lt=today,
                        status__in=[
                            TaskStatus.TODO,
                            TaskStatus.IN_PROGRESS,
                            TaskStatus.IN_REVIEW,
                        ],
                        then=1,
                    )
                )
            ),
            due_today=Count(Case(When(due_date=today, then=1))),
            personal_count=Count(Case(When(project__isnull=True, then=1))),
            project_count=Count(Case(When(project__isnull=False, then=1))),
        )

        return {
            "total_tasks": metrics["total"] or 0,
            "todo": metrics["todo"] or 0,
            "in_progress": metrics["in_progress"] or 0,
            "in_review": metrics["in_review"] or 0,
            "completed": metrics["completed"] or 0,
            "cancelled": metrics["cancelled"] or 0,
            "high_priority": metrics["high_priority"] or 0,
            "critical_priority": metrics["critical_priority"] or 0,
            "overdue": metrics["overdue"] or 0,
            "due_today": metrics["due_today"] or 0,
            "personal_tasks": metrics["personal_count"] or 0,
            "project_tasks": metrics["project_count"] or 0,
        }

    @classmethod
    def get_project_task_summary(
        cls,
        *,
        company: Union[Company, int],
        project_id: int,
    ) -> Dict[str, Any]:
        """
        Project-specific metric builder that formats summaries for Project view integration.
        Calculates task progress percentage alongside status counts in 1 SQL query.
        """
        metrics = cls.get_task_metrics_summary(
            company=company,
            project_id=project_id,
        )

        total = metrics["total_tasks"]
        completed = metrics["completed"]
        progress_percentage = int((completed / total) * 100) if total > 0 else 0

        return {
            "total": total,
            "todo": metrics["todo"],
            "in_progress": metrics["in_progress"],
            "review": metrics["in_review"],
            "completed": completed,
            "cancelled": metrics["cancelled"],
            "overdue": metrics["overdue"],
            "due_today": metrics["due_today"],
            "progress_percentage": progress_percentage,
        }