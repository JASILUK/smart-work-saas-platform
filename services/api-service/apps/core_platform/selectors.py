from apps.core_platform.models import PlatformRole


class PlatformRoleSelector:

    @staticmethod
    def list_roles():
        return (
            PlatformRole.objects.prefetch_related("permissions").all().order_by("name")
        )

    @staticmethod
    def get_role(role_id):
        return (
            PlatformRole.objects.prefetch_related("permissions")
            .filter(id=role_id)
            .first()
        )
