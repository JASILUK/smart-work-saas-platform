class CompanyContextService:

    def get_company_context(self, request):

        membership = request.membership
        company = request.company
        subscription = request.subscription

        permissions = membership.role.permissions.values_list("code", flat=True)

        return {
            "membership_id":membership.id,
            "company": {
                "id": company.id,
                "name": company.name,
                "slug": company.slug,
            },
            "role": {
                "id": membership.role.id,
                "name": membership.role.name,
            },
            "permissions": list(permissions),
            "subscription": self._serialize_subscription(subscription),
        }

    def _serialize_subscription(self, subscription):

        if not subscription:
            return None

        return {
            "plan": subscription.plan.code,
            "status": subscription.status,
            "trial_ends_at": subscription.trial_ends_at,
        }
