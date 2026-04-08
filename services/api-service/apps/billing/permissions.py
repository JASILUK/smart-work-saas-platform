from rest_framework.permissions import BasePermission

from apps.billing.models import Subscription


class ActiveSubscriptionPermission(BasePermission):

    def has_permission(self, request, view):

        company = getattr(request, "company", None)

        if not company:
            return True

        subscription = getattr(company, "subscription", None)

        if not subscription:
            return False

        if subscription.status in [
            Subscription.Status.EXPIRED,
            Subscription.Status.PAST_DUE,
        ]:
            return False

        request.subscription = subscription

        return True
