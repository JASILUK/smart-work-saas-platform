from django.core.exceptions import ValidationError

from apps.rbac.models import Permission


class PermissionService:

    @staticmethod
    def create_permission(data):

        if Permission.objects.filter(code=data["code"]).exists():
            raise ValidationError("Permission code already exists")

        permission = Permission.objects.create(**data)

        return permission

    @staticmethod
    def update_permission(permission, data):
        if Permission.objects.filter(code=data["code"]).exists():
            raise ValidationError("Permission code already exists")
        permission.code = data.get("code", permission.code)
        permission.name = data.get("name", permission.name)
        permission.description = data.get("description", permission.description)
        permission.category = data.get("category", permission.category)

        permission.save()

        return permission

    @staticmethod
    def delete_permission(permission):

        permission.delete()
