import fnmatch

from django.db import transaction

from apps.core.exceptions import ApplicationError
from apps.rbac.conf import TENANT_ROLE_BLUEPRINTS
from apps.rbac.models import Permission, Role


class RoleService:
    @transaction.atomic
    def create_default_roles(self, company):
        """Called when a new company is verified."""
        all_permissions = list(Permission.objects.all())
        owner_role = None

        for role_name, config in TENANT_ROLE_BLUEPRINTS.items():
            role = Role.objects.create(
                company=company, name=role_name, is_system_role=True
            )

            patterns = config.get("patterns", [])
            target_perms = [
                p
                for p in all_permissions
                if any(fnmatch.fnmatch(p.code, pat) for pat in patterns)
            ]
            role.permissions.set(target_perms)

            if role_name == "Owner":
                owner_role = role

        return owner_role

    @staticmethod
    def get_company_roles(company):
        return Role.objects.filter(company=company)

    def create_role(self, data, company):

        name = data.get("name")

        if Role.objects.filter(company=company, name__iexact=name).exists():

            raise ApplicationError(message="Role with this name already exists.")

        role = Role.objects.create(company=company, name=name)

        permissions = data.get("permissions")

        if permissions:
            role.permissions.set(permissions)

        return role

    def update_role(self, role, data):

        if role.is_system_role:
            raise ApplicationError(message="System roles cannot be modified.")

        role.name = data.get("name", role.name)

        permissions = data.get("permissions")

        if permissions is not None:
            role.permissions.set(permissions)

        role.save()

        return role

    def delete_role(self, role):

        if role.is_system_role:
            raise ApplicationError(message="System roles cannot be deleted.")

        role.delete()
