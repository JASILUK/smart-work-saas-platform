from datetime import timedelta

from django.utils import timezone

from apps.billing.models import Plan, Subscription


class SubscriptionService:

    def create_trial_subscription(self, company):

        plan = Plan.objects.filter(code="starter", is_active=True).first()

        return Subscription.objects.create(
            company=company,
            plan=plan,
            status=Subscription.Status.TRIALING,
            trial_ends_at=timezone.now() + timedelta(days=plan.trial_days),
        )

    def get_company_subscription(self, company):

        subscription = (
            Subscription.objects.filter(company=company).select_related("plan").first()
        )

        if not subscription:
            return None

        return {
            "plan": subscription.plan.code,
            "status": subscription.status,
            "trial_ends_at": subscription.trial_ends_at,
        }
