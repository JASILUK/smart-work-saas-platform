from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class TaskStatus(models.TextChoices):
    TODO = "todo", _("To Do")
    IN_PROGRESS = "in_progress", _("In Progress")
    IN_REVIEW = "in_review", _("In Review")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")


class TaskPriority(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
    CRITICAL = "critical", _("Critical")


class Task(TimeStampedModel):
    """
    Core Task domain model supporting both Project Tasks and Personal Tasks.

    - Personal Task: project is NULL
    - Project Task:  project references a valid Project instance

    Multi-tenant via company relation. References Membership for user ops.
    """

    Status = TaskStatus
    Priority = TaskPriority

    # =========================================================================
    # TENANCY & DOMAIN RELATIONS
    # =========================================================================
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="tasks",
        help_text=_("The tenant company owning this task."),
    )

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="tasks",
        help_text=_("Optional project association. If NULL, this is a Personal Task."),
    )

    created_by = models.ForeignKey(
        "companies.Membership",
        on_delete=models.PROTECT,
        related_name="created_tasks",
        help_text=_("The employee membership who created this task."),
    )

    assigned_to = models.ForeignKey(
        "companies.Membership",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
        help_text=_("The employee membership currently assigned to execute this task."),
    )

    # =========================================================================
    # TASK CONTENT & ATTRIBUTES
    # =========================================================================
    title = models.CharField(
        max_length=255,
        help_text=_("Concise title or summary of the task."),
    )

    description = models.TextField(
        blank=True,
        default="",
        help_text=_("Detailed description, requirements, or instructions."),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
        help_text=_("Current state of the task in the execution lifecycle."),
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        help_text=_("Urgency level of the task."),
    )

    # =========================================================================
    # SCHEDULE & TIMESTAMPS
    # =========================================================================
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Optional planned start date."),
    )

    due_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Optional target deadline date."),
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when the task was marked completed."),
    )

    # =========================================================================
    # METADATA & INDEXES
    # =========================================================================
    class Meta:
        db_table = "tasks"
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["company", "status"],
                name="task_company_status_idx",
            ),
            models.Index(
                fields=["company", "assigned_to", "status"],
                name="task_company_assignee_idx",
            ),
            models.Index(
                fields=["project", "status"],
                name="task_project_status_idx",
            ),
            models.Index(
                fields=["company", "project", "created_by"],
                name="task_personal_idx",
            ),
            models.Index(
                fields=["due_date"],
                name="task_due_date_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"

    @property
    def is_personal(self) -> bool:
        """Returns True if this task is a personal item not tied to any project."""
        return self.project_id is None

    @property
    def is_project_task(self) -> bool:
        """Returns True if this task belongs to a specific project."""
        return self.project_id is not None