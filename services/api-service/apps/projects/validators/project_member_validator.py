from typing import Optional, List, Dict, Any
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.projects.selectors.project_selector import ProjectSelector
from apps.projects.selectors.project_member_selector import ProjectMemberSelector
from apps.companies.selectors.membership_selector import MembershipSelector
from apps.projects.models.project_members import ProjectMember


class ProjectMemberValidator:
    """
    Business rule validator for ProjectMember operations.

    Validates all membership lifecycle operations before service execution.
    Reads exclusively through selectors. Never writes to the database.
    """

    MAX_BULK_MEMBERS = 100
    MAX_NOTES_LENGTH = 255
    VALID_ROLES = {
        ProjectMember.Role.OWNER,
        ProjectMember.Role.MANAGER,
        ProjectMember.Role.MEMBER,
    }

    # ================================================================
    # HELPER METHODS
    # ================================================================

    @classmethod
    def _check_project_exists_and_active(
        cls,
        project_id: int,
        company_id: int,
    ) -> tuple:
        errors: Dict[str, list] = {}
        project = ProjectSelector.get_by_id(
            company=company_id,
            project_id=project_id,
        )
        if not project:
            errors["project"] = [_("Project not found.")]
            return None, errors

        if project.is_archived:
            errors["project"] = [_("Cannot modify members of an archived project.")]

        return project, errors

    @classmethod
    def _check_membership_exists(
        cls,
        membership_id: int,
        company_id: int,
        field_name: str = "membership",
    ) -> Dict[str, list]:
        errors: Dict[str, list] = {}
        if not MembershipSelector.exists(
            membership_id=membership_id,
            company_id=company_id,
        ):
            errors[field_name] = [_(
                "Membership does not exist or does not belong to this company."
            )]
        return errors

    @classmethod
    def _check_actor_is_owner(
        cls,
        project_id: int,
        actor_membership_id: int,
    ) -> Dict[str, list]:
        errors: Dict[str, list] = {}
        is_member_owner = ProjectMemberSelector.is_owner(
            project_id=project_id,
            membership_id=actor_membership_id,
        )
        project = ProjectSelector.get_by_id(company=None, project_id=project_id)
        is_project_fk_owner = bool(project and project.owner_id == actor_membership_id)

        if not (is_member_owner or is_project_fk_owner):
            errors["actor"] = [_("Only the project Owner may perform this action.")]
        return errors

    @classmethod
    def _check_actor_can_manage(
        cls,
        project_id: int,
        actor_membership_id: int,
    ) -> Dict[str, list]:
        errors: Dict[str, list] = {}

        # Direct Project FK Owner check
        project = ProjectSelector.get_by_id(company=None, project_id=project_id)
        if project and project.owner_id == actor_membership_id:
            return errors

        # ProjectMember Owner/Manager check
        if not ProjectMemberSelector.can_manage_members(
            project_id=project_id,
            membership_id=actor_membership_id,
        ):
            errors["actor"] = [_(
                "Only project Owners or Managers may manage members."
            )]
        return errors

    @classmethod
    def _check_role_valid(
        cls,
        role: str,
        field_name: str = "role",
    ) -> Dict[str, list]:
        errors: Dict[str, list] = {}
        if role not in cls.VALID_ROLES:
            errors[field_name] = [_(
                "Invalid role. Must be one of: %(roles)s."
            ) % {"roles": ", ".join(cls.VALID_ROLES)}]
        return errors

    @classmethod
    def _check_notes_length(
        cls,
        notes: Optional[str],
        field_name: str = "notes",
    ) -> Dict[str, list]:
        errors: Dict[str, list] = {}
        if notes and len(notes) > cls.MAX_NOTES_LENGTH:
            errors[field_name] = [_(
                "Notes cannot exceed %(max)d characters."
            ) % {"max": cls.MAX_NOTES_LENGTH}]
        return errors

    # ================================================================
    # VALIDATE ADD MEMBER
    # ================================================================

    @classmethod
    def validate_add_member(
        cls,
        *,
        project_id: int,
        company_id: int,
        membership_id: int,
        role: str,
        notes: Optional[str] = None,
        actor_membership_id: int,
    ) -> None:
        errors: Dict[str, list] = {}

        project, project_errors = cls._check_project_exists_and_active(
            project_id=project_id,
            company_id=company_id,
        )
        errors.update(project_errors)

        errors.update(cls._check_membership_exists(
            membership_id=membership_id,
            company_id=company_id,
            field_name="membership",
        ))

        errors.update(cls._check_actor_can_manage(
            project_id=project_id,
            actor_membership_id=actor_membership_id,
        ))

        errors.update(cls._check_role_valid(role=role))
        errors.update(cls._check_notes_length(notes=notes))

        if not errors.get("membership") and not errors.get("project"):
            if ProjectMemberSelector.exists(
                project_id=project_id,
                membership_id=membership_id,
            ):
                errors["membership"] = [_(
                    "This user is already a member of the project."
                )]

        if not errors.get("actor") and not errors.get("role"):
            is_actor_owner = ProjectMemberSelector.is_owner(
                project_id=project_id,
                membership_id=actor_membership_id,
            ) or (project and project.owner_id == actor_membership_id)

            if not is_actor_owner and role in (
                ProjectMember.Role.OWNER,
                ProjectMember.Role.MANAGER,
            ):
                errors["role"] = [_(
                    "Only the project Owner may assign %(role)s role."
                ) % {"role": role}]

        if errors:
            raise ValidationError(errors)

    # ================================================================
    # VALIDATE BULK ADD MEMBERS
    # ================================================================

    @classmethod
    def validate_bulk_add_members(
        cls,
        *,
        project_id: int,
        company_id: int,
        members: List[Dict[str, Any]],
        actor_membership_id: int,
    ) -> None:
        errors: Dict[str, list] = {}

        if len(members) > cls.MAX_BULK_MEMBERS:
            errors["members"] = [_(
                "Cannot add more than %(max)d members at once."
            ) % {"max": cls.MAX_BULK_MEMBERS}]

        project, project_errors = cls._check_project_exists_and_active(
            project_id=project_id,
            company_id=company_id,
        )
        errors.update(project_errors)

        errors.update(cls._check_actor_can_manage(
            project_id=project_id,
            actor_membership_id=actor_membership_id,
        ))

        is_actor_owner = False
        if not errors.get("actor"):
            is_actor_owner = ProjectMemberSelector.is_owner(
                project_id=project_id,
                membership_id=actor_membership_id,
            ) or (project and project.owner_id == actor_membership_id)

        membership_ids = [m.get("membership_id") for m in members]
        if len(membership_ids) != len(set(membership_ids)):
            errors["members"] = errors.get("members", []) + [
                _("Duplicate membership IDs found in the batch.")
            ]

        for index, member_data in enumerate(members):
            prefix = f"members[{index}]"

            m_id = member_data.get("membership_id")
            role = member_data.get("role", ProjectMember.Role.MEMBER)
            notes = member_data.get("notes")

            if not m_id:
                errors[f"{prefix}.membership_id"] = [_("Membership ID is required.")]
                continue

            if not MembershipSelector.exists(
                membership_id=m_id,
                company_id=company_id,
            ):
                errors[f"{prefix}.membership_id"] = [_(
                    "Membership does not exist or does not belong to this company."
                )]
                continue

            if ProjectMemberSelector.exists(
                project_id=project_id,
                membership_id=m_id,
            ):
                errors[f"{prefix}.membership_id"] = [_(
                    "This user is already a member of the project."
                )]

            role_errors = cls._check_role_valid(role=role, field_name=f"{prefix}.role")
            errors.update(role_errors)

            if not is_actor_owner and role in (
                ProjectMember.Role.OWNER,
                ProjectMember.Role.MANAGER,
            ):
                errors[f"{prefix}.role"] = errors.get(f"{prefix}.role", []) + [
                    _("Only the project Owner may assign %(role)s role.") % {"role": role}
                ]

            errors.update(cls._check_notes_length(
                notes=notes,
                field_name=f"{prefix}.notes",
            ))

        if errors:
            raise ValidationError(errors)

    # ================================================================
    # VALIDATE UPDATE MEMBER
    # ================================================================

    @classmethod
    def validate_update_member(
        cls,
        *,
        project_id: int,
        company_id: int,
        member_id: int,
        role: Optional[str] = None,
        notes: Optional[str] = None,
        actor_membership_id: int,
    ) -> None:
        errors: Dict[str, list] = {}

        project, project_errors = cls._check_project_exists_and_active(
            project_id=project_id,
            company_id=company_id,
        )
        errors.update(project_errors)

        target_member = ProjectMemberSelector.get_by_id(member_id=member_id)
        if not target_member:
            errors["member"] = [_("Member not found.")]
        elif target_member.project_id != project_id:
            errors["member"] = [_("Member does not belong to this project.")]

        errors.update(cls._check_actor_can_manage(
            project_id=project_id,
            actor_membership_id=actor_membership_id,
        ))

        if role is not None:
            errors.update(cls._check_role_valid(role=role))

        if notes is not None:
            errors.update(cls._check_notes_length(notes=notes))

        if not errors.get("actor") and not errors.get("member") and target_member:
            is_actor_owner = ProjectMemberSelector.is_owner(
                project_id=project_id,
                membership_id=actor_membership_id,
            ) or (project and project.owner_id == actor_membership_id)
            is_target_owner = target_member.role == ProjectMember.Role.OWNER

            if not is_actor_owner and not ProjectMemberSelector.is_manager(
                project_id=project_id,
                membership_id=actor_membership_id,
            ):
                errors["actor"] = [_("You do not have permission to edit members.")]

            elif not is_actor_owner:
                if is_target_owner:
                    errors["actor"] = [_("Managers cannot edit the project Owner.")]

                if target_member.role == ProjectMember.Role.MANAGER:
                    errors["actor"] = [_("Managers cannot edit other Managers.")]

                if role in (ProjectMember.Role.OWNER, ProjectMember.Role.MANAGER):
                    errors["role"] = [_(
                        "Managers cannot assign %(role)s role."
                    ) % {"role": role}]

            if is_actor_owner:
                if is_target_owner and role is not None and role != ProjectMember.Role.OWNER:
                    errors["role"] = [_(
                        "Use the ownership transfer endpoint to change project ownership."
                    )]

        if errors:
            raise ValidationError(errors)

    # ================================================================
    # VALIDATE REMOVE MEMBER
    # ================================================================

    @classmethod
    def validate_remove_member(
        cls,
        *,
        project_id: int,
        company_id: int,
        member_id: int,
        actor_membership_id: int,
    ) -> None:
        errors: Dict[str, list] = {}

        project, project_errors = cls._check_project_exists_and_active(
            project_id=project_id,
            company_id=company_id,
        )
        errors.update(project_errors)

        target_member = ProjectMemberSelector.get_by_id(member_id=member_id)
        if not target_member:
            errors["member"] = [_("Member not found.")]
        elif target_member.project_id != project_id:
            errors["member"] = [_("Member does not belong to this project.")]

        errors.update(cls._check_actor_can_manage(
            project_id=project_id,
            actor_membership_id=actor_membership_id,
        ))

        if not errors.get("actor") and not errors.get("member") and target_member:
            is_actor_owner = ProjectMemberSelector.is_owner(
                project_id=project_id,
                membership_id=actor_membership_id,
            ) or (project and project.owner_id == actor_membership_id)
            is_target_owner = target_member.role == ProjectMember.Role.OWNER
            is_target_manager = target_member.role == ProjectMember.Role.MANAGER

            if not is_actor_owner:
                if is_target_owner:
                    errors["actor"] = [_("Managers cannot remove the project Owner.")]
                if is_target_manager:
                    errors["actor"] = [_("Managers cannot remove other Managers.")]

            if is_actor_owner and target_member.membership_id == actor_membership_id:
                owner_count = ProjectMemberSelector.count_members_by_role(
                    project_id=project_id,
                )["owners"]
                if owner_count <= 1:
                    errors["member"] = [_(
                        "Cannot remove yourself as the sole project Owner. "
                        "Transfer ownership first."
                    )]

            total_members = ProjectMemberSelector.count_members(project_id=project_id)
            if total_members <= 1:
                errors["member"] = [_(
                    "Cannot remove the last member from a project."
                )]

        if errors:
            raise ValidationError(errors)

    # ================================================================
    # VALIDATE TRANSFER OWNERSHIP
    # ================================================================

    @classmethod
    def validate_transfer_ownership(
        cls,
        *,
        project_id: int,
        company_id: int,
        new_owner_membership_id: int,
        actor_membership_id: int,
    ) -> None:
        errors: Dict[str, list] = {}

        project, project_errors = cls._check_project_exists_and_active(
            project_id=project_id,
            company_id=company_id,
        )
        errors.update(project_errors)

        errors.update(cls._check_actor_is_owner(
            project_id=project_id,
            actor_membership_id=actor_membership_id,
        ))

        errors.update(cls._check_membership_exists(
            membership_id=new_owner_membership_id,
            company_id=company_id,
            field_name="new_owner",
        ))

        if new_owner_membership_id == actor_membership_id:
            errors["new_owner"] = [_("Cannot transfer ownership to yourself.")]

        if not errors.get("new_owner"):
            new_owner_member = ProjectMemberSelector.get_project_member(
                project_id=project_id,
                membership_id=new_owner_membership_id,
            )
            if not new_owner_member:
                errors["new_owner"] = [_(
                    "The new owner must be an existing member of the project."
                )]
            elif new_owner_member.role == ProjectMember.Role.OWNER:
                errors["new_owner"] = [_(
                    "The selected member is already the project Owner."
                )]

        if errors:
            raise ValidationError(errors)