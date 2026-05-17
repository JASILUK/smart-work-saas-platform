# apps/companies/services/DepartmentService.py

from typing import Optional

from django.db import transaction

from apps.companies.models import (
    Department,
    Membership,
)

from apps.companies.selectors.DepartmentSelectors import (
    DepartmentSelector,
)

from apps.core.exceptions import ValidationError


class DepartmentService:

    # =====================================================
    # PARTIAL UPDATE SENTINEL
    # =====================================================

    UNSET = object()

    # =====================================================
    # CREATE DEPARTMENT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def create(
        *,
        company,
        name: str,
        parent=None,
        head=None,
        description: Optional[str] = None,
    ):

        cleaned_name = (
            name or ""
        ).strip()

        if not cleaned_name:

            raise ValidationError(
                "Department name required"
            )

        if DepartmentSelector.exists_with_name(
            company=company,
            name=cleaned_name,
        ):

            raise ValidationError(
                f"Department '{cleaned_name}' already exists"
            )

        if parent:

            DepartmentService._validate_parent(
                company=company,
                parent=parent,
            )

        if head:

            DepartmentService._validate_head(
                company=company,
                head=head,
            )

        department = Department.objects.create(

            company=company,

            name=cleaned_name,

            parent=parent,

            head=head,

            description=(
                description.strip()
                if description
                else None
            ),
        )

        return department

    # =====================================================
    # UPDATE DEPARTMENT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def update(
        *,
        department,
        name=UNSET,
        parent=UNSET,
        head=UNSET,
        description=UNSET,
    ):

        # =================================================
        # NAME
        # =================================================

        if name is not DepartmentService.UNSET:

            cleaned_name = (
                name or ""
            ).strip()

            if not cleaned_name:

                raise ValidationError(
                    "Department name required"
                )

            if (
                cleaned_name != department.name
                and
                DepartmentSelector.exists_with_name(
                    company=department.company,
                    name=cleaned_name,
                    exclude_id=department.id,
                )
            ):

                raise ValidationError(
                    f"Department '{cleaned_name}' already exists"
                )

            department.name = cleaned_name

        # =================================================
        # DESCRIPTION
        # =================================================

        if description is not DepartmentService.UNSET:

            department.description = (
                description.strip()
                if description
                else None
            )

        # =================================================
        # PARENT
        # =================================================

        if parent is not DepartmentService.UNSET:

            if parent is not None:

                if parent.id == department.id:

                    raise ValidationError(
                        "Department cannot be its own parent"
                    )

                DepartmentService._validate_parent(
                    company=department.company,
                    parent=parent,
                )

                if DepartmentService._is_descendant(
                    ancestor=department,
                    potential_descendant=parent,
                ):

                    raise ValidationError(
                        "Cannot move department under child department"
                    )

            department.parent = parent

        # =================================================
        # HEAD
        # =================================================

        if head is not DepartmentService.UNSET:

            if head is not None:

                DepartmentService._validate_head(
                    company=department.company,
                    head=head,
                )

            department.head = head

        department.save()

        return department

    # =====================================================
    # DELETE DEPARTMENT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def delete(
        *,
        department,
    ):

        has_members = (
            Membership.objects.filter(
                department=department,
                is_active=True,
            )
            .exists()
        )

        if has_members:

            raise ValidationError(
                "Cannot delete department with active members"
            )

        has_children = (
            department.children.exists()
        )

        if has_children:

            raise ValidationError(
                "Cannot delete parent department with child departments"
            )

        department.delete()

    # =====================================================
    # ASSIGN HEAD
    # =====================================================

    @staticmethod
    @transaction.atomic
    def assign_head(
        *,
        department,
        membership,
    ):

        DepartmentService._validate_head(
            company=department.company,
            head=membership,
        )

        department.head = membership

        department.save(
            update_fields=[
                "head",
                "updated_at",
            ]
        )

        return department

    # =====================================================
    # REMOVE HEAD
    # =====================================================

    @staticmethod
    @transaction.atomic
    def remove_head(
        *,
        department,
    ):

        department.head = None

        department.save(
            update_fields=[
                "head",
                "updated_at",
            ]
        )

        return department

    # =====================================================
    # VALIDATE PARENT
    # =====================================================

    @staticmethod
    def _validate_parent(
        *,
        company,
        parent,
    ):

        if parent.company_id != company.id:

            raise ValidationError(
                "Parent must belong to same company"
            )

    # =====================================================
    # VALIDATE HEAD
    # =====================================================

    @staticmethod
    def _validate_head(
        *,
        company,
        head,
    ):

        if head.company_id != company.id:

            raise ValidationError(
                "Department head must belong to same company"
            )

        if not head.is_active:

            raise ValidationError(
                "Department head membership inactive"
            )

    # =====================================================
    # CHECK DESCENDANT
    # =====================================================

    @staticmethod
    def _is_descendant(
        *,
        ancestor,
        potential_descendant,
    ):

        current = (
            potential_descendant.parent
        )

        while current:

            if current.id == ancestor.id:
                return True

            current = current.parent

        return False