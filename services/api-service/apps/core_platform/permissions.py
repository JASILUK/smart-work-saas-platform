from rest_framework.permissions import BasePermission


class PlatformPermission(BasePermission):

    def has_permission(self, request, view):

        profile = getattr(request.user, "platform_profile", None)

        if not profile:
            return False

        if not profile.is_active:
            return False

        required_permissions = getattr(view, "required_permissions", {})

        permission_code = required_permissions.get(request.method)

        if not permission_code:
            return True

        user_permissions = {p.code for p in profile.role.permissions.all()}

        return permission_code in user_permissions
