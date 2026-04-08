from rest_framework.permissions import BasePermission


class RolePermission(BasePermission):

    def has_permission(self, request, view):

        membership = getattr(request, "membership", None)

        if not membership:
            return False

        required_permissions = getattr(view, "required_permissions", {})

        permission_code = required_permissions.get(request.method)

        # if endpoint doesn't require permission
        if not permission_code:
            return True

        user_permissions = {p.code for p in membership.role.permissions.all()}

        return permission_code in user_permissions
