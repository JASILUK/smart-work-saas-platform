# companies/services/membership_service.py

from apps.billing.selectors import get_subscription_for_company
from apps.companies.models import Membership


class MembershipService:

    def get_user_memberships(self, user):

        return Membership.objects.select_related("company").filter(
            user=user, is_active=True
        )

    def get_subscription_data(self, company):

        subscription = get_subscription_for_company(company.id)

        if not subscription:
            return None

        return {
            "plan": subscription.plan.code,
            "status": subscription.status,
            "trial_ends_at": subscription.trial_ends_at,
        }
