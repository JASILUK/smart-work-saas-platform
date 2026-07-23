from datetime import date, datetime
from typing import Any, Dict, Optional, Union

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.companies.models import Company, Membership
from apps.companies.selectors.membership_selector import MembershipSelector
from apps.projects.models.projects import Project
from apps.projects.selectors.project_member_selector import ProjectMemberSelector
from apps.projects.selectors.project_selector import ProjectSelector
from apps.tasks.models.tasks import Task, TaskPriority, TaskStatus
from apps.tasks.selectors.task_selector import TaskSelector


# Global sentinel object for omitted fields
UNSET = object()


def is_unset(value: Any) -> bool:
    """Helper to check if a keyword argument was omitted or passed as a sentinel object."""
    if value is None:
        return False
    if isinstance(value, (int, str, date, datetime)):
        return False
    return True


class TaskValidator:
    """
    Business rule validator for the Task domain model.

    Enforces data integrity, multi-tenant boundaries, cross-field invariants,
    and project membership constraints before service execution.

    Reads exclusively through Selectors. Never writes to the database.
    Used strictly by TaskService.
    """

    MIN_TITLE_LENGTH = 2
    MAX_TITLE_LENGTH = 255
    MAX_DESCRIPTION_LENGTH = 5000

    VALID_STATUSES = set(TaskStatus.values)
    VALID_PRIORITIES = set(TaskPriority.values)

    # =========================================================================
    # PRIVATE DOMAIN HELPERS
    # =========================================================================

    @classmethod
    def _validate_title(cls, title: Optional[str], errors: Dict[str, list]) -> None:
        """Enforces title presence, non-whitespace, and length bounds."""
        if title is None or not title.strip():
            errors["title"] = [_("Task title is required and cannot be blank.")]
            return

        cleaned_title = title.strip()
        if len(cleaned_title) < cls.MIN_TITLE_LENGTH:
            errors["title"] = [
                _("Task title must be at least %(min)d characters.")
                % {"min": cls.MIN_TITLE_LENGTH}
            ]
        elif len(cleaned_title) > cls.MAX_TITLE_LENGTH:
            errors["title"] = [
                _("Task title cannot exceed %(max)d characters.")
                % {"max": cls.MAX_TITLE_LENGTH}
            ]

    @classmethod
    def _validate_description(
        cls, description: Optional[str], errors: Dict[str, list]
    ) -> None:
        """Enforces max length restrictions on task description."""
        if description and len(description) > cls.MAX_DESCRIPTION_LENGTH:
            errors["description"] = [
                _("Description cannot exceed %(max)d characters.")
                % {"max": cls.MAX_DESCRIPTION_LENGTH}
            ]

    @classmethod
    def _validate_dates(
        cls,
        start_date: Optional[date],
        due_date: Optional[date],
        errors: Dict[str, list],
    ) -> None:
        """Enforces start_date <= due_date invariant."""
        if start_date and due_date and start_date > due_date:
            errors["due_date"] = [_("Target due date must be on or after start date.")]

    @classmethod
    def _validate_completion_timestamps(
        cls,
        status: Optional[str],
        completed_at: Optional[datetime],
        errors: Dict[str, list],
    ) -> None:
        """
        Enforces state invariants for task completion:
        - Non-completed task status CANNOT have a completed_at timestamp set.
        """
        if status and status != TaskStatus.COMPLETED and completed_at is not None:
            errors["completed_at"] = [
                _("Completion timestamp can only be set when task status is Completed.")
            ]

    @classmethod
    def _validate_tenant_alignment(
        cls,
        *,
        company_id: int,
        project_id: Optional[int] = None,
        created_by_id: Optional[int] = None,
        assigned_to_id: Optional[int] = None,
        errors: Dict[str, list],
    ) -> Optional[Project]:
        """
        Validates multi-tenant scoping across Company, Project, Creator, and Assignee.
        Returns resolved Project instance if valid.
        """
        project = None

        # 1. Project Tenant Check
        if project_id is not None:
            project = ProjectSelector.get_by_id(
                company_id=company_id, project_id=project_id
            )
            if not project:
                errors["project"] = [
                    _("Project not found or does not belong to this company.")
                ]
            elif project.is_archived:
                errors["project"] = [
                    _("Cannot modify or create tasks in an archived project.")
                ]

        # 2. Creator Membership Tenant Check
        if created_by_id is not None:
            if not MembershipSelector.exists(
                membership_id=created_by_id, company_id=company_id
            ):
                errors["created_by"] = [
                    _("Creator membership does not exist in this company.")
                ]

        # 3. Assignee Membership Tenant Check
        if assigned_to_id is not None:
            if not MembershipSelector.exists(
                membership_id=assigned_to_id, company_id=company_id
            ):
                errors["assigned_to"] = [
                    _("Assigned employee membership does not exist in this company.")
                ]

        return project

    @classmethod
    def _validate_project_membership(
        cls,
        *,
        project_id: int,
        membership_id: int,
        field_name: str,
        error_message: str,
        errors: Dict[str, list],
    ) -> None:
        """
        Enforces that a membership belongs to a project using ProjectMemberSelector.
        """
        if not ProjectMemberSelector.exists(
            project_id=project_id, membership_id=membership_id
        ):
            errors[field_name] = [error_message]

    # =========================================================================
    # PUBLIC SERVICE VALIDATION ENTRYPOINTS
    # =========================================================================

    @classmethod
    def validate_create_task(
        cls,
        *,
        company_id: int,
        created_by_id: int,
        title: str,
        description: Optional[str] = "",
        status: str = TaskStatus.TODO,
        priority: str = TaskPriority.MEDIUM,
        project_id: Optional[int] = None,
        assigned_to_id: Optional[int] = None,
        start_date: Optional[date] = None,
        due_date: Optional[date] = None,
        completed_at: Optional[datetime] = None,
    ) -> None:
        """
        Validates business rules for task creation (Personal and Project Tasks).
        """
        errors: Dict[str, list] = {}

        # 1. Content Boundaries
        cls._validate_title(title, errors)
        cls._validate_description(description, errors)

        # 2. Enum Choices
        if status not in cls.VALID_STATUSES:
            errors["status"] = [_("Invalid task status choice.")]

        if priority not in cls.VALID_PRIORITIES:
            errors["priority"] = [_("Invalid task priority choice.")]

        # 3. Dates & Completion Invariants
        cls._validate_dates(start_date, due_date, errors)
        cls._validate_completion_timestamps(status, completed_at, errors)

        # 4. Multi-Tenant Alignment
        project = cls._validate_tenant_alignment(
            company_id=company_id,
            project_id=project_id,
            created_by_id=created_by_id,
            assigned_to_id=assigned_to_id,
            errors=errors,
        )

        # 5. Project Membership Boundaries (Only for Project Tasks)
        if project_id and not errors.get("project"):
            if created_by_id and not errors.get("created_by"):
                cls._validate_project_membership(
                    project_id=project_id,
                    membership_id=created_by_id,
                    field_name="created_by",
                    error_message=_(
                        "Task creator must be an existing member of the target project."
                    ),
                    errors=errors,
                )

            if assigned_to_id and not errors.get("assigned_to"):
                cls._validate_project_membership(
                    project_id=project_id,
                    membership_id=assigned_to_id,
                    field_name="assigned_to",
                    error_message=_(
                        "Assigned employee must be an existing member of the target project."
                    ),
                    errors=errors,
                )

        if errors:
            raise ValidationError(errors)

    @classmethod
    def validate_update_task(
        cls,
        *,
        company_id: int,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        project_id: Any = UNSET,
        assigned_to_id: Any = UNSET,
        start_date: Optional[date] = None,
        due_date: Optional[date] = None,
        completed_at: Optional[datetime] = None,
    ) -> Task:
        """
        Validates task update payloads against current state in database.
        Returns existing Task model instance if valid.
        """
        errors: Dict[str, list] = {}

        # 1. Existence & Tenant Isolation
        task = TaskSelector.get_by_id(company=company_id, task_id=task_id)
        if not task:
            errors["task"] = [_("Task not found.")]
            raise ValidationError(errors)

        # 2. Content Checks (if supplied)
        if title is not None:
            cls._validate_title(title, errors)

        if description is not None:
            cls._validate_description(description, errors)

        # 3. Enum Checks (if supplied)
        effective_status = status if status is not None else task.status
        if status is not None and status not in cls.VALID_STATUSES:
            errors["status"] = [_("Invalid task status choice.")]

        if priority is not None and priority not in cls.VALID_PRIORITIES:
            errors["priority"] = [_("Invalid task priority choice.")]

        # 4. Dates & Completion Invariants
        effective_start = start_date if start_date is not None else task.start_date
        effective_due = due_date if due_date is not None else task.due_date
        cls._validate_dates(effective_start, effective_due, errors)

        effective_completed_at = (
            completed_at if completed_at is not None else task.completed_at
        )
        cls._validate_completion_timestamps(
            effective_status, effective_completed_at, errors
        )

        # 5. Resolve Effective Scope Changes safely
        effective_project_id = task.project_id if is_unset(project_id) else project_id
        effective_assignee_id = task.assigned_to_id if is_unset(assigned_to_id) else assigned_to_id

        # 6. Tenant Alignment Checks
        if (
            effective_project_id != task.project_id
            or effective_assignee_id != task.assigned_to_id
        ):
            cls._validate_tenant_alignment(
                company_id=company_id,
                project_id=effective_project_id,
                assigned_to_id=effective_assignee_id,
                errors=errors,
            )

        # 7. Project Membership Checks
        if effective_project_id and effective_assignee_id and not errors.get("assigned_to"):
            cls._validate_project_membership(
                project_id=effective_project_id,
                membership_id=effective_assignee_id,
                field_name="assigned_to",
                error_message=_(
                    "Assigned employee must be an existing member of the target project."
                ),
                errors=errors,
            )

        if errors:
            raise ValidationError(errors)

        return task

    @classmethod
    def validate_delete_task(
        cls,
        *,
        company_id: int,
        task_id: int,
    ) -> Task:
        """
        Validates task deletion business rules. Returns Task instance.
        """
        errors: Dict[str, list] = {}

        task = TaskSelector.get_by_id(company=company_id, task_id=task_id)
        if not task:
            errors["task"] = [_("Task not found.")]
            raise ValidationError(errors)

        if task.status == TaskStatus.COMPLETED:
            errors["task"] = [
                _("Completed tasks cannot be deleted. Reopen or archive the task first.")
            ]

        if errors:
            raise ValidationError(errors)

        return task

    @classmethod
    def validate_assign_task(
        cls,
        *,
        company_id: int,
        task_id: int,
        assigned_to_id: int,
    ) -> Task:
        """
        Validates task assignment to an employee membership.
        """
        errors: Dict[str, list] = {}

        task = TaskSelector.get_by_id(company=company_id, task_id=task_id)
        if not task:
            errors["task"] = [_("Task not found.")]
            raise ValidationError(errors)

        if not MembershipSelector.exists(
            membership_id=assigned_to_id, company_id=company_id
        ):
            errors["assigned_to"] = [
                _("Target assignee does not exist in this company.")
            ]
        elif task.project_id:
            cls._validate_project_membership(
                project_id=task.project_id,
                membership_id=assigned_to_id,
                field_name="assigned_to",
                error_message=_(
                    "Assigned employee is not a member of the target project."
                ),
                errors=errors,
            )

        if errors:
            raise ValidationError(errors)

        return task

    @classmethod
    def validate_unassign_task(
        cls,
        *,
        company_id: int,
        task_id: int,
    ) -> Task:
        """
        Validates clearing task assignment.
        """
        errors: Dict[str, list] = {}

        task = TaskSelector.get_by_id(company=company_id, task_id=task_id)
        if not task:
            errors["task"] = [_("Task not found.")]
            raise ValidationError(errors)

        return task

    @classmethod
    def validate_change_status(
        cls,
        *,
        company_id: int,
        task_id: int,
        new_status: str,
    ) -> Task:
        """
        Validates arbitrary status transitions.
        """
        errors: Dict[str, list] = {}

        task = TaskSelector.get_by_id(company=company_id, task_id=task_id)
        if not task:
            errors["task"] = [_("Task not found.")]
            raise ValidationError(errors)

        if new_status not in cls.VALID_STATUSES:
            errors["status"] = [_("Invalid task status choice.")]

        if errors:
            raise ValidationError(errors)

        return task

    @classmethod
    def validate_complete_task(
        cls,
        *,
        company_id: int,
        task_id: int,
        completed_at: Optional[datetime] = None,
    ) -> Task:
        """
        Validates marking a task as Completed.
        """
        errors: Dict[str, list] = {}

        task = TaskSelector.get_by_id(company=company_id, task_id=task_id)
        if not task:
            errors["task"] = [_("Task not found.")]
            raise ValidationError(errors)

        if task.status == TaskStatus.COMPLETED:
            errors["status"] = [_("Task is already marked as Completed.")]

        if errors:
            raise ValidationError(errors)

        return task

    @classmethod
    def validate_reopen_task(
        cls,
        *,
        company_id: int,
        task_id: int,
    ) -> Task:
        """
        Validates reopening a completed or cancelled task.
        """
        errors: Dict[str, list] = {}

        task = TaskSelector.get_by_id(company=company_id, task_id=task_id)
        if not task:
            errors["task"] = [_("Task not found.")]
            raise ValidationError(errors)

        if task.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            errors["status"] = [
                _("Only Completed or Cancelled tasks can be reopened.")
            ]

        if errors:
            raise ValidationError(errors)

        return task

    @classmethod
    def validate_cancel_task(
        cls,
        *,
        company_id: int,
        task_id: int,
    ) -> Task:
        """
        Validates cancelling a task.
        """
        errors: Dict[str, list] = {}

        task = TaskSelector.get_by_id(company=company_id, task_id=task_id)
        if not task:
            errors["task"] = [_("Task not found.")]
            raise ValidationError(errors)

        if task.status == TaskStatus.CANCELLED:
            errors["status"] = [_("Task is already marked as Cancelled.")]

        if errors:
            raise ValidationError(errors)

        return task