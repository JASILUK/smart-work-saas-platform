from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.companies.models import Membership
from apps.core.models import TimeStampedModel
from apps.projects.models.projects import Project


class ProjectMemberRole(models.TextChoices):
    OWNER = "owner", _("Owner")
    MANAGER = "manager", _("Manager")
    MEMBER = "member", _("Member")


class ProjectMember(TimeStampedModel):
    """
    Connects employees (Membership) to Projects with role-based access.

    Multi-tenant via Project -> Company.
    Enforces exactly one Owner per project.
    """

    Role = ProjectMemberRole

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="memberships",
        help_text=_("The project this membership belongs to."),
    )

    membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name="project_memberships",
        help_text=_("The employee participating in the project."),
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        help_text=_("Project-level authority: Owner, Manager, or Member."),
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp when the member was added to the project."),
    )

    added_by = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_members_added",
        help_text=_("The employee who invited or added this member."),
    )

    notes = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Optional context for this membership (e.g., role description)."),
    )

    class Meta:
        db_table = "project_members"
        verbose_name = _("Project Member")
        verbose_name_plural = _("Project Members")
        ordering = ["-joined_at"]

        unique_together = ["project", "membership"]

        # Partial unique index: only one owner per project
        # Note: Used string 'owner' inside Q() to prevent NameError in Meta scope
        constraints = [
            models.UniqueConstraint(
                fields=["project"],
                condition=Q(role="owner"),
                name="single_owner_per_project",
                violation_error_message=_("A project can have only one Owner."),
            ),
        ]

        indexes = [
            models.Index(
                fields=["project", "role"],
                name="project_role_idx",
            ),
            models.Index(
                fields=["membership", "project"],
                name="membership_project_idx",
            ),
            models.Index(
                fields=["role"],
                name="role_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.membership} in {self.project} ({self.role})"

    def clean(self):
        super().clean()

        if self.membership.company_id != self.project.company_id:
            raise ValidationError(
                {"membership": _("Member must belong to the same company as the project.")}
            )

        if self.added_by and self.added_by.company_id != self.project.company_id:
            raise ValidationError(
                {"added_by": _("Inviter must belong to the same company as the project.")}
            )

        if (
            self.pk
            and self.role != self.Role.OWNER
            and getattr(self, "_original_role", None) == self.Role.OWNER
        ):
            owner_count = ProjectMember.objects.filter(
                project=self.project, role=self.Role.OWNER
            ).count()
            if owner_count <= 1:
                raise ValidationError(
                    {"role": _("Cannot demote the only Owner. Transfer ownership first.")}
                )

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                self._original_role = ProjectMember.objects.get(pk=self.pk).role
            except ProjectMember.DoesNotExist:
                self._original_role = None
        else:
            self._original_role = None

        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_owner(self) -> bool:
        return self.role == self.Role.OWNER

    @property
    def is_manager(self) -> bool:
        return self.role == self.Role.MANAGER

    @property
    def is_member(self) -> bool:
        return self.role == self.Role.MEMBER

    @property
    def can_manage_members(self) -> bool:
        return self.role in (self.Role.OWNER, self.Role.MANAGER)