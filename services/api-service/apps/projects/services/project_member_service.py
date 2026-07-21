from typing import Optional, List, Dict, Any
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError, ObjectDoesNotExist

from apps.projects.models.projects import Project
from apps.projects.models.project_members import ProjectMember
from apps.projects.selectors.project_selector import ProjectSelector
from apps.projects.selectors.project_member_selector import ProjectMemberSelector
from apps.projects.validators.project_member_validator import ProjectMemberValidator


class ProjectMemberService:
    """
    Exclusive write orchestrator for ProjectMember operations.

    The only layer that creates, updates, or deletes ProjectMember records.
    All writes wrapped in transactions. All reads delegated to selectors.
    All validations delegated to validators.
    """

    @classmethod
    def _get_project(
        cls,
        project_id: int,
        company_id: int,
    ) -> Project:
        project = ProjectSelector.get_by_id(
            company=company_id,
            project_id=project_id,
        )
        if not project:
            raise ObjectDoesNotExist("Project not found.")
        return project

    @classmethod
    def _get_member(
        cls,
        member_id: int,
    ) -> ProjectMember:
        member = ProjectMemberSelector.get_by_id(member_id=member_id)
        if not member:
            raise ObjectDoesNotExist("Project member not found.")
        return member

    @classmethod
    def _get_member_by_membership(
        cls,
        project_id: int,
        membership_id: int,
    ) -> Optional[ProjectMember]:
        return ProjectMemberSelector.get_project_member(
            project_id=project_id,
            membership_id=membership_id,
        )

    @classmethod
    def _get_owner(
        cls,
        project_id: int,
    ) -> ProjectMember:
        owner_qs = ProjectMemberSelector.get_project_owners(project_id=project_id)
        owner = owner_qs.first()
        if not owner:
            raise ObjectDoesNotExist("Project owner not found.")
        return owner

    @classmethod
    def create_owner(
        cls,
        *,
        project: Project,
        membership_id: int,
    ) -> ProjectMember:
        return ProjectMember.objects.create(
            project=project,
            membership_id=membership_id,
            role=ProjectMember.Role.OWNER,
            added_by_id=membership_id,
            notes="Project Creator / Owner",
        )

    @classmethod
    def _create_member(
        cls,
        *,
        project_id: int,
        membership_id: int,
        role: str,
        added_by_id: int,
        notes: Optional[str] = None,
    ) -> ProjectMember:
        return ProjectMember.objects.create(
            project_id=project_id,
            membership_id=membership_id,
            role=role,
            added_by_id=added_by_id,
            notes=notes or "",
        )

    @classmethod
    def _update_member(
        cls,
        member: ProjectMember,
        *,
        role: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> ProjectMember:
        update_fields = []

        if role is not None:
            member.role = role
            update_fields.append("role")

        if notes is not None:
            member.notes = notes
            update_fields.append("notes")

        if update_fields:
            member.save(update_fields=update_fields)

        return member

    @classmethod
    def _delete_member(
        cls,
        member: ProjectMember,
    ) -> Dict[str, Any]:
        deleted_info = {
            "id": member.id,
            "membership_id": member.membership_id,
            "role": member.role,
            "project_id": member.project_id,
        }
        member.delete()
        return deleted_info

    @classmethod
    def list_members(
        cls,
        *,
        project_id: int,
        company_id: int,
        membership,
        search: Optional[str] = None,
        role: Optional[str] = None,
        ordering: Optional[str] = None,
    ):
        cls._get_project(project_id=project_id, company_id=company_id)

        return ProjectMemberSelector.search_members(
            project_id=project_id,
            search=search,
            role=role,
            ordering=ordering,
        )

    @classmethod
    def add_member(
        cls,
        *,
        project_id: int,
        company_id: int,
        membership_id: int,
        role: str = ProjectMember.Role.MEMBER,
        notes: Optional[str] = None,
        actor_membership_id: int,
    ) -> ProjectMember:
        ProjectMemberValidator.validate_add_member(
            project_id=project_id,
            company_id=company_id,
            membership_id=membership_id,
            role=role,
            notes=notes,
            actor_membership_id=actor_membership_id,
        )

        with transaction.atomic():
            member = cls._create_member(
                project_id=project_id,
                membership_id=membership_id,
                role=role,
                added_by_id=actor_membership_id,
                notes=notes,
            )

            project = cls._get_project(
                project_id=project_id,
                company_id=company_id,
            )
            project.updated_by_id = actor_membership_id
            project.save(update_fields=["updated_by", "updated_at"])

        return member

    @classmethod
    def bulk_add_members(
        cls,
        *,
        project_id: int,
        company_id: int,
        members: List[Dict[str, Any]],
        actor_membership_id: int,
    ) -> List[ProjectMember]:
        ProjectMemberValidator.validate_bulk_add_members(
            project_id=project_id,
            company_id=company_id,
            members=members,
            actor_membership_id=actor_membership_id,
        )

        with transaction.atomic():
            member_objects = []
            for member_data in members:
                member_objects.append(ProjectMember(
                    project_id=project_id,
                    membership_id=member_data["membership_id"],
                    role=member_data.get("role", ProjectMember.Role.MEMBER),
                    added_by_id=actor_membership_id,
                    notes=member_data.get("notes", ""),
                ))

            created_members = ProjectMember.objects.bulk_create(member_objects)

            project = cls._get_project(
                project_id=project_id,
                company_id=company_id,
            )
            project.updated_by_id = actor_membership_id
            project.save(update_fields=["updated_by", "updated_at"])

        return created_members

    @classmethod
    def update_member(
        cls,
        *,
        project_id: int,
        company_id: int,
        member_id: int,
        role: Optional[str] = None,
        notes: Optional[str] = None,
        actor_membership_id: int,
    ) -> ProjectMember:
        ProjectMemberValidator.validate_update_member(
            project_id=project_id,
            company_id=company_id,
            member_id=member_id,
            role=role,
            notes=notes,
            actor_membership_id=actor_membership_id,
        )

        with transaction.atomic():
            member = cls._get_member(member_id=member_id)
            member = cls._update_member(member, role=role, notes=notes)

            if role is not None:
                project = cls._get_project(
                    project_id=project_id,
                    company_id=company_id,
                )
                project.updated_by_id = actor_membership_id
                project.save(update_fields=["updated_by", "updated_at"])

        return member

    @classmethod
    def remove_member(
        cls,
        *,
        project_id: int,
        company_id: int,
        member_id: int,
        actor_membership_id: int,
    ) -> Dict[str, Any]:
        ProjectMemberValidator.validate_remove_member(
            project_id=project_id,
            company_id=company_id,
            member_id=member_id,
            actor_membership_id=actor_membership_id,
        )

        with transaction.atomic():
            member = cls._get_member(member_id=member_id)
            deleted_info = cls._delete_member(member)

            project = cls._get_project(
                project_id=project_id,
                company_id=company_id,
            )
            project.updated_by_id = actor_membership_id
            project.save(update_fields=["updated_by", "updated_at"])

        return deleted_info

    @classmethod
    def transfer_ownership(
        cls,
        *,
        project_id: int,
        company_id: int,
        new_owner_membership_id: int,
        actor_membership_id: int,
    ) -> Dict[str, Any]:
        # Validate business rules
        ProjectMemberValidator.validate_transfer_ownership(
            project_id=project_id,
            company_id=company_id,
            new_owner_membership_id=new_owner_membership_id,
            actor_membership_id=actor_membership_id,
        )

        with transaction.atomic():
            current_owner = cls._get_owner(project_id=project_id)
            new_owner_member = cls._get_member_by_membership(
                project_id=project_id,
                membership_id=new_owner_membership_id,
            )

            if not new_owner_member:
                raise ObjectDoesNotExist(
                    "New owner must be an existing project member."
                )

            # Direct QuerySet updates bypass full_clean() checks during swap state
            ProjectMember.objects.filter(id=current_owner.id).update(
                role=ProjectMember.Role.MANAGER
            )
            ProjectMember.objects.filter(id=new_owner_member.id).update(
                role=ProjectMember.Role.OWNER
            )

            # Update Project foreign key
            project = cls._get_project(
                project_id=project_id,
                company_id=company_id,
            )
            project.owner_id = new_owner_membership_id
            project.updated_by_id = actor_membership_id
            project.save(update_fields=["owner", "updated_by", "updated_at"])

            # Reload instances for response structure
            current_owner.refresh_from_db()
            new_owner_member.refresh_from_db()

            result = {
                "old_owner": {
                    "membership_id": current_owner.membership_id,
                    "role": current_owner.role,
                },
                "new_owner": {
                    "membership_id": new_owner_member.membership_id,
                    "role": new_owner_member.role,
                },
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "owner_id": project.owner_id,
                },
            }

        return result