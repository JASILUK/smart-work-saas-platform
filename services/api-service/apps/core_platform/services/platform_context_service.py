class PlatformContextService:

    def get_platform_context(self, request):

        profile = request.user.platform_profile

        permissions = profile.role.permissions.values_list("code", flat=True)

        return {
            "user": {
                "id": request.user.id,
                "email": request.user.email,
            },
            "role": {
                "id": profile.role.id,
                "name": profile.role.name,
            },
            "permissions": list(permissions),
        }
