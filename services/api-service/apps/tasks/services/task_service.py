from datetime import date, datetime
from typing import Any, Dict, Optional, Union

from django.db import transaction
from django.utils import timezone

from apps.companies.models import Company, Membership
from apps.tasks.models.tasks import Task, TaskPriority, TaskStatus
from apps.tasks.selectors.task_selector import TaskSelector
from apps.tasks.validators.task_validator import TaskValidator


class TaskService:
    """
    Exclusive write orchestrator for Task operations.

    Handles creation, updates, deletion, assignment, and status transitions.
    All write operations are wrapped in atomic transactions and delegate data
    integrity validation directly to TaskValidator.
    """

    # Sentinel object for differentiating explicit None/null from omitted kwargs
    _UNSET = object()

    # =========================================================================
    # EVENT & INTEGRATION HOOKS (FUTURE EXTENSIONS)
    # =========================================================================

    @classmethod
    def _on_task_created(cls, task: Task) -> None:
        """
        Hook executed after successful task creation.
        Future integrations: NotificationService, ActivityLog, Realtime Websockets.
        """
        pass

    @classmethod
    def _on_task_updated(cls, task: Task, updated_fields: list) -> None:
        """
        Hook executed after successful task update.
        """
        pass

    @classmethod
    def _on_task_deleted(cls, task_info: Dict[str, Any]) -> None:
        """
        Hook executed after successful task deletion.
        """
        pass

    @classmethod
    def _on_task_assigned(
        cls, task: Task, previous_assignee_id: Optional[int]
    ) -> None:
        """
        Hook executed when task assignee changes.
        """
        pass

    @classmethod
    def _on_task_status_changed(cls, task: Task, previous_status: str) -> None:
        """
        Hook executed when task status changes.
        """
        pass

    # =========================================================================
    # PUBLIC WRITE SERVICE METHODS
    # =========================================================================

    @classmethod
    def create_task(
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
    ) -> Task:
        """
        Create a Personal Task (project_id=None) or Project Task (project_id=int).
        Executes validation and creates the task within an atomic transaction.
        """
        # 1. Enforce business rules & tenant boundaries
        TaskValidator.validate_create_task(
            company_id=company_id,
            created_by_id=created_by_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            project_id=project_id,
            assigned_to_id=assigned_to_id,
            start_date=start_date,
            due_date=due_date,
            completed_at=completed_at,
        )

        # 2. Maintain completed_at timestamp invariant
        if status == TaskStatus.COMPLETED and completed_at is None:
            completed_at = timezone.now()

        # 3. Persist atomically
        with transaction.atomic():
            task = Task.objects.create(
                company_id=company_id,
                created_by_id=created_by_id,
                project_id=project_id,
                assigned_to_id=assigned_to_id,
                title=title.strip(),
                description=description or "",
                status=status,
                priority=priority,
                start_date=start_date,
                due_date=due_date,
                completed_at=completed_at if status == TaskStatus.COMPLETED else None,
            )

            # Re-fetch instance via selector to ensure all select_related fields are pre-loaded
            task = TaskSelector.get_by_id(company=company_id, task_id=task.id)

            # Trigger event hook
            cls._on_task_created(task)

        return task

    @classmethod
    def update_task(
        cls,
        *,
        company_id: int,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        project_id: Any = _UNSET,
        assigned_to_id: Any = _UNSET,
        start_date: Optional[date] = None,
        due_date: Optional[date] = None,
        completed_at: Optional[datetime] = None,
    ) -> Task:
        """
        Update selective fields on an existing task without overwriting unchanged values.
        """
        # 1. Validate payload against current task state
        task = TaskValidator.validate_update_task(
            company_id=company_id,
            task_id=task_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            project_id=project_id,
            assigned_to_id=assigned_to_id,
            start_date=start_date,
            due_date=due_date,
            completed_at=completed_at,
        )

        update_fields = []
        previous_status = task.status

        # 2. Apply field modifications
        if title is not None:
            task.title = title.strip()
            update_fields.append("title")

        if description is not None:
            task.description = description
            update_fields.append("description")

        if priority is not None:
            task.priority = priority
            update_fields.append("priority")

        if start_date is not None:
            task.start_date = start_date
            update_fields.append("start_date")

        if due_date is not None:
            task.due_date = due_date
            update_fields.append("due_date")

        if project_id is not cls._UNSET:
            task.project_id = project_id
            update_fields.append("project")

        if assigned_to_id is not cls._UNSET:
            task.assigned_to_id = assigned_to_id
            update_fields.append("assigned_to")

        # Handle status transitions and completed_at invariants
        if status is not None and status != task.status:
            task.status = status
            update_fields.append("status")

            if status == TaskStatus.COMPLETED:
                task.completed_at = completed_at or timezone.now()
                update_fields.append("completed_at")
            else:
                task.completed_at = None
                update_fields.append("completed_at")

        # 3. Persist atomically
        if update_fields:
            update_fields.append("updated_at")
            with transaction.atomic():
                task.save(update_fields=update_fields)

                # Re-fetch instance with full relations
                task = TaskSelector.get_by_id(company=company_id, task_id=task.id)

                cls._on_task_updated(task, update_fields)
                if "status" in update_fields:
                    cls._on_task_status_changed(task, previous_status)

        return task

    @classmethod
    def delete_task(
        cls,
        *,
        company_id: int,
        task_id: int,
    ) -> Dict[str, Any]:
        """
        Delete a task record after validating deletion rules.
        Returns dictionary containing deleted task metadata for API response context.
        """
        task = TaskValidator.validate_delete_task(
            company_id=company_id,
            task_id=task_id,
        )

        task_info = {
            "id": task.id,
            "title": task.title,
            "company_id": task.company_id,
            "project_id": task.project_id,
        }

        with transaction.atomic():
            task.delete()
            cls._on_task_deleted(task_info)

        return task_info

    @classmethod
    def assign_task(
        cls,
        *,
        company_id: int,
        task_id: int,
        assigned_to_id: int,
    ) -> Task:
        """
        Assign or reassign a task to a target employee membership.
        """
        task = TaskValidator.validate_assign_task(
            company_id=company_id,
            task_id=task_id,
            assigned_to_id=assigned_to_id,
        )

        previous_assignee_id = task.assigned_to_id

        with transaction.atomic():
            task.assigned_to_id = assigned_to_id
            task.save(update_fields=["assigned_to", "updated_at"])

            task = TaskSelector.get_by_id(company=company_id, task_id=task.id)
            cls._on_task_assigned(task, previous_assignee_id)

        return task

    @classmethod
    def unassign_task(
        cls,
        *,
        company_id: int,
        task_id: int,
    ) -> Task:
        """
        Clear assignee from a task record (`assigned_to = None`).
        """
        task = TaskValidator.validate_unassign_task(
            company_id=company_id,
            task_id=task_id,
        )

        previous_assignee_id = task.assigned_to_id

        with transaction.atomic():
            task.assigned_to = None
            task.save(update_fields=["assigned_to", "updated_at"])

            task = TaskSelector.get_by_id(company=company_id, task_id=task.id)
            cls._on_task_assigned(task, previous_assignee_id)

        return task

    @classmethod
    def change_status(
        cls,
        *,
        company_id: int,
        task_id: int,
        new_status: str,
    ) -> Task:
        """
        Transition task status and maintain completed_at timestamps automatically.
        """
        task = TaskValidator.validate_change_status(
            company_id=company_id,
            task_id=task_id,
            new_status=new_status,
        )

        previous_status = task.status

        with transaction.atomic():
            task.status = new_status
            update_fields = ["status", "updated_at"]

            if new_status == TaskStatus.COMPLETED:
                task.completed_at = timezone.now()
                update_fields.append("completed_at")
            else:
                task.completed_at = None
                update_fields.append("completed_at")

            task.save(update_fields=update_fields)

            task = TaskSelector.get_by_id(company=company_id, task_id=task.id)
            cls._on_task_status_changed(task, previous_status)

        return task

    @classmethod
    def complete_task(
        cls,
        *,
        company_id: int,
        task_id: int,
        completed_at: Optional[datetime] = None,
    ) -> Task:
        """
        Explicitly transition task status to COMPLETED and set completed_at.
        """
        task = TaskValidator.validate_complete_task(
            company_id=company_id,
            task_id=task_id,
            completed_at=completed_at,
        )

        previous_status = task.status

        with transaction.atomic():
            task.status = TaskStatus.COMPLETED
            task.completed_at = completed_at or timezone.now()
            task.save(update_fields=["status", "completed_at", "updated_at"])

            task = TaskSelector.get_by_id(company=company_id, task_id=task.id)
            cls._on_task_status_changed(task, previous_status)

        return task

    @classmethod
    def reopen_task(
        cls,
        *,
        company_id: int,
        task_id: int,
        target_status: str = TaskStatus.TODO,
    ) -> Task:
        """
        Reopen a completed or cancelled task back into work lifecycle.
        Clears completed_at timestamp.
        """
        task = TaskValidator.validate_reopen_task(
            company_id=company_id,
            task_id=task_id,
        )

        previous_status = task.status

        with transaction.atomic():
            task.status = target_status
            task.completed_at = None
            task.save(update_fields=["status", "completed_at", "updated_at"])

            task = TaskSelector.get_by_id(company=company_id, task_id=task.id)
            cls._on_task_status_changed(task, previous_status)

        return task

    @classmethod
    def cancel_task(
        cls,
        *,
        company_id: int,
        task_id: int,
    ) -> Task:
        """
        Transition task status to CANCELLED.
        """
        task = TaskValidator.validate_cancel_task(
            company_id=company_id,
            task_id=task_id,
        )

        previous_status = task.status

        with transaction.atomic():
            task.status = TaskStatus.CANCELLED
            task.completed_at = None
            task.save(update_fields=["status", "completed_at", "updated_at"])

            task = TaskSelector.get_by_id(company=company_id, task_id=task.id)
            cls._on_task_status_changed(task, previous_status)

        return task