# platform/services/platform_service.py


class PlatformService:

    def get_platform_identity(self, user):

        return {
            "account_type": "platform",
            "user": {"id": user.id, "email": user.email},
        }

    def get_platform_context(self, user):

        profile = user.platform_profile

        permissions = profile.role.permissions.values_list("code", flat=True)

        return {
            "role": {
                "id": profile.role.id,
                "name": profile.role.name,
            },
            "permissions": list(permissions),
        }
