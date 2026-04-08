from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from apps.rbac.models import Permission, Role


class RoleSelector:

    @staticmethod
    def list_company_roles(company):

        return (
            Role.objects.filter(company=company)
            .prefetch_related("permissions")
            .order_by("name")
        )

    @staticmethod
    def get_role(role_id, company):

        return (
            Role.objects.filter(id=role_id, company=company)
            .prefetch_related("permissions")
            .first()
        )


class PermissionSelector:

    @staticmethod
    def list_tenant_permissions():
        return Permission.objects.filter(scope="tenant").order_by("category")

    @staticmethod
    def list_all_permissions():
        return Permission.objects.all().order_by("category", "name")

    @staticmethod
    def list_platform_permissions():
        return Permission.objects.filter(scope="platform").order_by("category", "name")

    @staticmethod
    def get_permission(permission_id):
        return Permission.objects.filter(id=permission_id).first()
