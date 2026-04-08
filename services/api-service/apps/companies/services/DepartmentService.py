# companies/services/department_service.py
from typing import Optional

from django.db import transaction

from apps.companies.models import Department
from apps.companies.selectors.DepartmentSelectors import DepartmentSelector
from apps.core.exceptions import ValidationError


class DepartmentService:
    """Business logic for departments."""

    @staticmethod
    @transaction.atomic
    def create(company, name: str, parent=None, description: Optional[str] = None):
        if DepartmentSelector.exists_with_name(company, name):
            raise ValidationError(f"Department '{name}' already exists")

        if parent and parent.company != company:
            raise ValidationError("Parent must be in same company")

        return Department.objects.create(
            company=company,
            name=name.strip(),
            description=description.strip() if description else None,
            parent=parent,
        )

    @staticmethod
    @transaction.atomic
    def update(
        department,
        name: Optional[str] = None,
        parent=None,
        description: Optional[str] = None,
    ):
        if name is not None and name != department.name:
            if DepartmentSelector.exists_with_name(
                department.company, name, department.pk
            ):
                raise ValidationError(f"Department '{name}' already exists")
            department.name = name.strip()

        if description is not None:
            department.description = description.strip() if description else None

        if parent is not None:
            if parent.pk == department.pk:
                raise ValidationError("Cannot be own parent")
            if parent.company != department.company:
                raise ValidationError("Parent must be in same company")
            if DepartmentService._is_descendant(department, parent):
                raise ValidationError("Cannot set child as parent")
            department.parent = parent

        department.save()
        return department

    @staticmethod
    @transaction.atomic
    def delete(department):
        department.delete()

    @staticmethod
    def _is_descendant(ancestor, potential_descendant):
        """Check if potential_descendant is under ancestor (prevent circular)."""
        current = potential_descendant.parent
        while current:
            if current.pk == ancestor.pk:
                return True
            current = current.parent
        return False
