from django.core.exceptions import ValidationError

from apps.core_platform.models import PlatformProfile, PlatformRole
from apps.rbac.models import Permission


class PlatformRoleService:

    @staticmethod
    def create_role(data):

        permissions = data.pop("permissions", [])

        role = PlatformRole.objects.create(**data)

        valid_permissions = Permission.objects.filter(
            id__in=permissions, scope="platform"
        )

        role.permissions.set(valid_permissions)

        return role

    @staticmethod
    def update_role(role, data):

        permissions = data.pop("permissions", None)

        role.name = data.get("name", role.name)

        role.save()

        if permissions is not None:

            valid_permissions = Permission.objects.filter(
                id__in=permissions, scope="platform"
            )

            role.permissions.set(valid_permissions)

        return role

    @staticmethod
    def delete_role(role):

        # Prevent deleting role assigned to users
        if PlatformProfile.objects.filter(role=role).exists():
            raise ValidationError("Cannot delete role assigned to platform users")

        role.delete()
