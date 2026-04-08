# users/services/session_service.py

from apps.companies.services.membership_service import MembershipService
from apps.core_platform.services.platform_service import PlatformService


class SessionService:

    def __init__(self):
        self.membership_service = MembershipService()
        self.platform_service = PlatformService()

    def get_user_session(self, user):

        if hasattr(user, "platform_profile"):
            return self.platform_service.get_platform_identity(user)

        return self._get_tenant_identity(user)

    def _get_tenant_identity(self, user):

        memberships = self.membership_service.get_user_memberships(user)

        companies = []

        for membership in memberships:
            company = membership.company

            companies.append(
                {"id": company.id, "name": company.name, "slug": company.slug}
            )

        return {
            "account_type": "tenant",
            "user": self._serialize_user(user),
            "companies": companies,
        }

    def _serialize_user(self, user):

        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_verified": user.is_verified,
        }

    def _serialize_user(self, user):
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_verified": user.is_verified,
        }
