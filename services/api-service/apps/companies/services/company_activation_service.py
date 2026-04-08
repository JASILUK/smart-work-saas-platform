from django.db import transaction

from apps.billing.services.subscription_service import SubscriptionService
from apps.companies.models import Membership
from apps.companies.selectors.Employee_selectors import get_pending_company_by_owner
from apps.rbac.services.role_service import RoleService


class CompanyActivationService:

    def __init__(self):
        self.role_service = RoleService()
        self.subscription_service = SubscriptionService()

    @transaction.atomic
    def activate_for_verified_user(self, user):

        company = get_pending_company_by_owner(user)
        if not company:
            return None

        company.status = company.Status.ACTIVE
        company.save()

        owner_role = self.role_service.create_default_roles(company)

        Membership.objects.create(user=user, company=company, role=owner_role)

        self.subscription_service.create_trial_subscription(company)

        return company
