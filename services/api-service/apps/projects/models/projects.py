from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

from apps.companies.models import Company, Membership
from apps.core.models import TimeStampedModel


class Project(TimeStampedModel):
    """
    Enterprise project model for internal project management.

    Multi-tenant by Company. Owned by a Membership.
    Supports public/private visibility and full project lifecycle.
    """

    class Visibility(models.TextChoices):
        PUBLIC = "public", _("Public")
        PRIVATE = "private", _("Private")

    class Status(models.TextChoices):
        PLANNING = "planning", _("Planning")
        ACTIVE = "active", _("Active")
        ON_HOLD = "on_hold", _("On Hold")
        COMPLETED = "completed", _("Completed")
        ARCHIVED = "archived", _("Archived")

    # Core Fields
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="projects",
        help_text=_("The company this project belongs to."),
    )

    owner = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_projects",
        help_text=_("The employee responsible for this project."),
    )

    name = models.CharField(
        max_length=255,
        help_text=_("Display name of the project."),
    )

    code = models.CharField(
        max_length=50,
        help_text=_("Unique identifier within the company (e.g., PROJ-001)."),
    )

    description = models.TextField(
        blank=True,
        help_text=_("Detailed description of the project scope and goals."),
    )

    # Visibility & Status
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
        help_text=_(
            "Public: any employee with view permission can access. "
            "Private: only explicit members can access."
        ),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNING,
        help_text=_("Current lifecycle state of the project."),
    )

    # Scheduling
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Planned or actual start date."),
    )

    end_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Planned or actual end date."),
    )

    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_(
            "Timestamp when the project was archived. "
            "Set automatically when status transitions to Archived."
        ),
    )

    # UI/UX
    color = models.CharField(
        max_length=7,
        default="#6366F1",
        help_text=_("Hex color for visual identification (e.g., #FF5733)."),
    )

    # Client Information (Inline)
    client_name = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Primary contact person at the client organization."),
    )

    client_company = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Name of the external client company."),
    )

    client_email = models.EmailField(
        blank=True,
        help_text=_("Email address of the client contact."),
    )

    client_phone = models.CharField(
        max_length=30,
        blank=True,
        help_text=_("Phone number of the client contact."),
    )

    # Audit Trail
    created_by = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects_created",
        help_text=_("The employee who created this project."),
    )

    updated_by = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects_updated",
        help_text=_("The employee who last modified this project."),
    )

    class Meta:
        db_table = "projects"
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")
        ordering = ["-created_at"]

        unique_together = ["company", "code"]

        indexes = [
            models.Index(
                fields=["company", "status"],
                name="company_status_idx",
            ),
            models.Index(
                fields=["company", "visibility"],
                name="company_visibility_idx",
            ),
            models.Index(
                fields=["company", "owner"],
                name="company_owner_idx",
            ),
            models.Index(
                fields=["company", "archived_at"],
                name="company_archived_at_idx",
            ),
            models.Index(
                fields=["status"],
                name="status_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                check=Q(start_date__isnull=True)
                | Q(end_date__isnull=True)
                | Q(start_date__lte=F("end_date")),
                name="check_start_before_end",
                violation_error_message=_("End date must be on or after start date."),
            ),
            models.CheckConstraint(
                check=Q(color__regex=r"^#[0-9A-Fa-f]{6}$"),
                name="check_valid_hex_color",
                violation_error_message=_(
                    "Color must be a valid 6-digit hex code (e.g., #6366F1)."
                ),
            ),
            models.CheckConstraint(
                check=~Q(status="archived") | Q(archived_at__isnull=False),
                name="check_archived_has_timestamp",
                violation_error_message=_(
                    "Archived projects must have an archived_at timestamp."
                ),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"

    def clean(self):
        super().clean()

        if self.owner and self.owner.company_id != self.company_id:
            raise ValidationError(
                {"owner": _("Project owner must be a member of the project's company.")}
            )

        if self.created_by and self.created_by.company_id != self.company_id:
            raise ValidationError(
                {"created_by": _("Project creator must be a member of the project's company.")}
            )

        if self.updated_by and self.updated_by.company_id != self.company_id:
            raise ValidationError(
                {"updated_by": _("Project updater must be a member of the project's company.")}
            )

        if self.status == self.Status.ARCHIVED and not self.archived_at:
            from django.utils import timezone
            self.archived_at = timezone.now()

        if self.status != self.Status.ARCHIVED and self.archived_at:
            self.archived_at = None

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_archived(self) -> bool:
        return self.status == self.Status.ARCHIVED

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE

    @property
    def display_dates(self) -> str:
        if self.start_date and self.end_date:
            return f"{self.start_date.strftime('%b %d, %Y')} – {self.end_date.strftime('%b %d, %Y')}"
        if self.start_date:
            return f"From {self.start_date.strftime('%b %d, %Y')}"
        if self.end_date:
            return f"Until {self.end_date.strftime('%b %d, %Y')}"
        return "No dates set"