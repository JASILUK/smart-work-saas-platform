from typing import Optional, List, Dict, Any
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied, ObjectDoesNotExist
from django.db.models import QuerySet

from apps.projects.models.projects import Project
from apps.projects.validators.project_validator import ProjectValidator
from apps.projects.selectors.project_selector import ProjectSelector


class ProjectService:
    """
    Business workflow orchestrator for Project operations.

    Coordinates validators, selectors, and future services to execute
    project lifecycle operations. Never queries ORM directly for reads.
    All reads delegated to ProjectSelector. All validations delegated
    to ProjectValidator.
    """

    # ================================================================
    # CREATE
    # ================================================================

    @classmethod
    def create_project(
        cls,
        *,
        company,
        name: str,
        code: str,
        description: str = "",
        color: str = "#6366F1",
        visibility: str = "private",
        status: str = "planning",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        owner_id: int,
        created_by_id: Optional[int] = None,
        client_name: str = "",
        client_company: str = "",
        client_email: str = "",
        client_phone: str = "",
        members: Optional[List[Dict[str, Any]]] = None,
    ) -> Project:
        """
        Create a new project with owner and optional members.
        """
        ProjectValidator.validate_create(
            company_id=company.id,
            name=name,
            code=code,
            description=description,
            color=color,
            visibility=visibility,
            status=status,
            start_date=start_date,
            end_date=end_date,
            owner_id=owner_id,
            created_by_id=created_by_id,
            client_name=client_name,
            client_company=client_company,
            client_email=client_email,
            client_phone=client_phone,
        )

        with transaction.atomic():
            project = Project.objects.create(
                company=company,
                name=name,
                code=code,
                description=description,
                color=color,
                visibility=visibility,
                status=status,
                start_date=start_date,
                end_date=end_date,
                owner_id=owner_id,
                created_by_id=created_by_id,
                client_name=client_name,
                client_company=client_company,
                client_email=client_email,
                client_phone=client_phone,
            )

            from apps.projects.services.project_member_service import ProjectMemberService

            ProjectMemberService.create_owner(
                project=project,
                membership_id=owner_id,
            )

            if members:
                ProjectMemberService.bulk_add_members(
                    project_id=project.id,
                    company_id=company.id,
                    members=members,
                    actor_membership_id=owner_id,
                )

        return project

    # ================================================================
    # UPDATE
    # ================================================================

    @classmethod
    def update_project(
        cls,
        *,
        project_id: int,
        company,
        membership,
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
    ) -> Project:
        """
        Update an existing project's editable fields.
        """
        editable_fields = {
            "name": name,
            "code": code,
            "description": description,
            "color": color,
            "visibility": visibility,
            "status": status,
            "start_date": start_date,
            "end_date": end_date,
            "owner_id": owner_id,
            "client_name": client_name,
            "client_company": client_company,
            "client_email": client_email,
            "client_phone": client_phone,
        }

        fields_to_update = {k: v for k, v in editable_fields.items() if v is not None}

        ProjectValidator.validate_update(
            project_id=project_id,
            company_id=company.id,
            **fields_to_update,
        )

        project = ProjectSelector.get_visible_project(
            company=company,
            membership=membership,
            project_id=project_id,
        )

        if not project:
            raise ObjectDoesNotExist("Project not found or access denied.")

        update_fields = []

        for field, value in fields_to_update.items():
            if field == "owner_id":
                setattr(project, "owner_id", value)
                update_fields.append("owner")
            else:
                setattr(project, field, value)
                update_fields.append(field)

        project.updated_by = membership
        update_fields.extend(["updated_by", "updated_at"])

        project.save(update_fields=update_fields)

        return project

    # ================================================================
    # ARCHIVE
    # ================================================================

    @classmethod
    def archive_project(
        cls,
        *,
        project_id: int,
        company,
        membership,
    ) -> Project:
        """
        Archive a project.
        """
        ProjectValidator.validate_archive(
            project_id=project_id,
            company_id=company.id,
        )

        project = ProjectSelector.get_visible_project(
            company=company,
            membership=membership,
            project_id=project_id,
        )

        if not project:
            raise ObjectDoesNotExist("Project not found or access denied.")

        project.status = Project.Status.ARCHIVED
        project.archived_at = timezone.now()
        project.updated_by = membership

        project.save(update_fields=["status", "archived_at", "updated_by", "updated_at"])

        return project

    # ================================================================
    # RESTORE
    # ================================================================

    @classmethod
    def restore_project(
        cls,
        *,
        project_id: int,
        company,
        membership,
    ) -> Project:
        """
        Restore an archived project to planning status.
        """
        ProjectValidator.validate_restore(
            project_id=project_id,
            company_id=company.id,
        )

        project = ProjectSelector.get_visible_project(
            company=company,
            membership=membership,
            project_id=project_id,
        )

        if not project:
            raise ObjectDoesNotExist("Project not found or access denied.")

        project.status = Project.Status.PLANNING
        project.archived_at = None
        project.updated_by = membership

        project.save(update_fields=["status", "archived_at", "updated_by", "updated_at"])

        return project

    # ================================================================
    # DELETE (Soft Delete Only)
    # ================================================================

    @classmethod
    def delete_project(
        cls,
        *,
        project_id: int,
        company,
        membership,
    ) -> Project:
        """
        Soft delete a project by archiving it.
        """
        project = ProjectSelector.get_visible_project(
            company=company,
            membership=membership,
            project_id=project_id,
        )

        if not project:
            raise ObjectDoesNotExist("Project not found or access denied.")

        project.status = Project.Status.ARCHIVED
        project.archived_at = timezone.now()
        project.updated_by = membership

        project.save(update_fields=["status", "archived_at", "updated_by", "updated_at"])

        return project

    # ================================================================
    # READ
    # ================================================================

    @classmethod
    def get_project(
        cls,
        *,
        project_id: int,
        company,
        membership,
    ) -> Project:
        """
        Retrieve a single project workspace instance if visible to membership.
        """
        project = ProjectSelector.get_visible_project(
            company=company,
            membership=membership,
            project_id=project_id,
        )

        if not project:
            raise ObjectDoesNotExist("Project not found or access denied.")

        return project

    @classmethod
    def list_projects(
        cls,
        *,
        company,
        membership,
        search: Optional[str] = None,
        status: Optional[str] = None,
        visibility: Optional[str] = None,
        owner: Optional[int] = None,
        ordering: Optional[str] = None,
    ) -> QuerySet[Project]:
        """
        List projects visible to the membership with optional filtering.
        """
        return ProjectSelector.search_projects(
            company=company,
            membership=membership,
            search=search,
            status=status,
            visibility=visibility,
            owner=owner,
            ordering=ordering,
        )