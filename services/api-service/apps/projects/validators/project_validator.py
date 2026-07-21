# apps/projects/validators/project_validator.py

import re
from typing import Any, Dict, Optional
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.projects.selectors.project_selector import ProjectSelector
from apps.companies.selectors.membership_selector import MembershipSelector


class ProjectValidator:
    """
    Business input validator for Project operations.
    
    Validates user input and business rules before service execution.
    All database reads delegated to selectors.
    """

    # ------------------------------------------------------------------
    # Constants
    # ------------------------------------------------------------------

    NAME_MIN_LENGTH = 1
    NAME_MAX_LENGTH = 255
    CODE_MIN_LENGTH = 1
    CODE_MAX_LENGTH = 50
    DESCRIPTION_MAX_LENGTH = 5000  # Practical enterprise limit
    COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")
    PHONE_MAX_LENGTH = 30
    VISIBILITY_CHOICES = {"public", "private"}
    STATUS_CHOICES = {"planning", "active", "on_hold", "completed", "archived"}

    # ------------------------------------------------------------------
    # validate_create
    # ------------------------------------------------------------------

    @classmethod
    def validate_create(
        cls,
        *,
        company_id: int,
        name: str,
        code: str,
        description: str = "",
        color: str = "#6366F1",
        visibility: str = "private",
        status: str = "planning",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        owner_id: Optional[int] = None,
        created_by_id: Optional[int] = None,
        client_name: str = "",
        client_company: str = "",
        client_email: str = "",
        client_phone: str = "",
    ) -> None:
        """
        Validate all business rules for Project creation.
        
        Raises ValidationError with field-level errors if invalid.
        """
        errors: Dict[str, list] = {}

        # ---- Name ----
        if not name or not isinstance(name, str):
            errors["name"] = [_("Project name is required.")]
        else:
            stripped_name = name.strip()
            if len(stripped_name) < cls.NAME_MIN_LENGTH:
                errors["name"] = [_("Project name cannot be empty.")]
            elif len(stripped_name) > cls.NAME_MAX_LENGTH:
                errors["name"] = [
                    _("Project name cannot exceed %(max)d characters.") % {"max": cls.NAME_MAX_LENGTH}
                ]

        # ---- Code ----
        if not code or not isinstance(code, str):
            errors["code"] = [_("Project code is required.")]
        else:
            stripped_code = code.strip()
            if len(stripped_code) < cls.CODE_MIN_LENGTH:
                errors["code"] = [_("Project code cannot be empty.")]
            elif len(stripped_code) > cls.CODE_MAX_LENGTH:
                errors["code"] = [
                    _("Project code cannot exceed %(max)d characters.") % {"max": cls.CODE_MAX_LENGTH}
                ]
            else:
                # Check company-scoped uniqueness via selector
                if ProjectSelector.exists_code(company_id=company_id, code=stripped_code):
                    errors["code"] = [_("A project with this code already exists in your company.")]

        # ---- Description ----
        if description and len(description) > cls.DESCRIPTION_MAX_LENGTH:
            errors["description"] = [
                _("Description cannot exceed %(max)d characters.") % {"max": cls.DESCRIPTION_MAX_LENGTH}
            ]

        # ---- Color ----
        if color and not cls.COLOR_PATTERN.match(color):
            errors["color"] = [_("Color must be a valid hex code (e.g., #6366F1).")]

        # ---- Visibility ----
        if visibility not in cls.VISIBILITY_CHOICES:
            errors["visibility"] = [_("Invalid visibility. Choose 'public' or 'private'.")]

        # ---- Status ----
        if status not in cls.STATUS_CHOICES:
            errors["status"] = [_("Invalid project status.")]

        # ---- Dates ----
        if start_date and end_date:
            if start_date > end_date:
                errors["end_date"] = [_("End date must be on or after start date.")]

        # ---- Owner ----
        if not owner_id:
            errors["owner"] = [_("Project owner is required.")]
        elif not MembershipSelector.exists(membership_id=owner_id, company_id=company_id):
            errors["owner"] = [_("Owner does not exist or does not belong to this company.")]

        # ---- Created By ----
        if created_by_id and not MembershipSelector.exists(
            membership_id=created_by_id, company_id=company_id
        ):
            errors["created_by"] = [_("Created by user does not exist or does not belong to this company.")]

        # ---- Client Email ----
        if client_email:
            # Basic format check beyond EmailField; business-level validation
            if "@" not in client_email or "." not in client_email.split("@")[-1]:
                errors["client_email"] = [_("Invalid email format.")]

        # ---- Client Phone ----
        if client_phone and len(client_phone) > cls.PHONE_MAX_LENGTH:
            errors["client_phone"] = [
                _("Phone number cannot exceed %(max)d characters.") % {"max": cls.PHONE_MAX_LENGTH}
            ]

        if errors:
            raise ValidationError(errors)

    # ------------------------------------------------------------------
    # validate_update
    # ------------------------------------------------------------------

    @classmethod
    def validate_update(
        cls,
        *,
        project_id: int,
        company_id: int,
        name: Optional[str] = None,
        code: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        visibility: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        owner_id: Optional[int] = None,
        client_name: Optional[str] = None,
        client_company: Optional[str] = None,
        client_email: Optional[str] = None,
        client_phone: Optional[str] = None,
        # Immutable fields that must be rejected if provided
        company_id_input: Optional[int] = None,
        created_by_id_input: Optional[int] = None,
    ) -> None:
        """
        Validate all business rules for Project update.
        
        Prevents editing immutable fields and archived projects.
        """
        errors: Dict[str, list] = {}

        # ---- Reject immutable fields ----
        if company_id_input is not None:
            errors["company"] = [_("Company cannot be changed.")]

        if created_by_id_input is not None:
            errors["created_by"] = [_("Created by cannot be changed.")]

        # ---- Check project exists and is not archived ----
        project = ProjectSelector.get_by_id(project_id=project_id, company_id=company_id)
        if not project:
            raise ValidationError({"project": [_("Project not found.")]})

        if project.is_archived:
            errors["project"] = [_("Cannot edit an archived project. Restore it first.")]

        # ---- Name ----
        if name is not None:
            if not isinstance(name, str):
                errors["name"] = [_("Invalid project name.")]
            else:
                stripped_name = name.strip()
                if len(stripped_name) < cls.NAME_MIN_LENGTH:
                    errors["name"] = [_("Project name cannot be empty.")]
                elif len(stripped_name) > cls.NAME_MAX_LENGTH:
                    errors["name"] = [
                        _("Project name cannot exceed %(max)d characters.") % {"max": cls.NAME_MAX_LENGTH}
                    ]

        # ---- Code ----
        if code is not None:
            if not isinstance(code, str):
                errors["code"] = [_("Invalid project code.")]
            else:
                stripped_code = code.strip()
                if len(stripped_code) < cls.CODE_MIN_LENGTH:
                    errors["code"] = [_("Project code cannot be empty.")]
                elif len(stripped_code) > cls.CODE_MAX_LENGTH:
                    errors["code"] = [
                        _("Project code cannot exceed %(max)d characters.") % {"max": cls.CODE_MAX_LENGTH}
                    ]
                else:
                    # Exclude current project from uniqueness check
                    if ProjectSelector.exists_code(
                        company_id=company_id,
                        code=stripped_code,
                        exclude_project_id=project_id,
                    ):
                        errors["code"] = [_("A project with this code already exists in your company.")]

        # ---- Description ----
        if description is not None and len(description) > cls.DESCRIPTION_MAX_LENGTH:
            errors["description"] = [
                _("Description cannot exceed %(max)d characters.") % {"max": cls.DESCRIPTION_MAX_LENGTH}
            ]

        # ---- Color ----
        if color is not None and not cls.COLOR_PATTERN.match(color):
            errors["color"] = [_("Color must be a valid hex code (e.g., #6366F1).")]

        # ---- Visibility ----
        if visibility is not None and visibility not in cls.VISIBILITY_CHOICES:
            errors["visibility"] = [_("Invalid visibility. Choose 'public' or 'private'.")]

        # ---- Status ----
        if status is not None and status not in cls.STATUS_CHOICES:
            errors["status"] = [_("Invalid project status.")]

        # ---- Dates ----
        if start_date is not None and end_date is not None:
            if start_date > end_date:
                errors["end_date"] = [_("End date must be on or after start date.")]

        # ---- Owner ----
        if owner_id is not None:
            if not MembershipSelector.exists(membership_id=owner_id, company_id=company_id):
                errors["owner"] = [_("Owner does not exist or does not belong to this company.")]

        # ---- Client Email ----
        if client_email is not None and client_email:
            if "@" not in client_email or "." not in client_email.split("@")[-1]:
                errors["client_email"] = [_("Invalid email format.")]

        # ---- Client Phone ----
        if client_phone is not None and len(client_phone) > cls.PHONE_MAX_LENGTH:
            errors["client_phone"] = [
                _("Phone number cannot exceed %(max)d characters.") % {"max": cls.PHONE_MAX_LENGTH}
            ]

        if errors:
            raise ValidationError(errors)

    # ------------------------------------------------------------------
    # validate_archive
    # ------------------------------------------------------------------

    @classmethod
    def validate_archive(
        cls,
        *,
        project_id: int,
        company_id: int,
    ) -> None:
        """
        Validate that a project can be archived.
        
        Rejects if already archived.
        """
        errors: Dict[str, list] = {}

        project = ProjectSelector.get_by_id(project_id=project_id, company_id=company_id)
        if not project:
            raise ValidationError({"project": [_("Project not found.")]})

        if project.is_archived:
            errors["project"] = [_("Project is already archived.")]

        if errors:
            raise ValidationError(errors)

    # ------------------------------------------------------------------
    # validate_restore
    # ------------------------------------------------------------------

    @classmethod
    def validate_restore(
        cls,
        *,
        project_id: int,
        company_id: int,
    ) -> None:
        """
        Validate that a project can be restored from archive.
        
        Rejects if not archived.
        """
        errors: Dict[str, list] = {}

        project = ProjectSelector.get_by_id(project_id=project_id, company_id=company_id)
        if not project:
            raise ValidationError({"project": [_("Project not found.")]})

        if not project.is_archived:
            errors["project"] = [_("Project is not archived.")]