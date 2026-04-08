# billing/selectors.py

from apps.billing.models import Plan, Subscription


def get_subscription_for_company(company_id):
    return (
        Subscription.objects.filter(company_id=company_id)
        .select_related("plan")
        .first()
    )


def get_active_plans():
    return Plan.objects.filter(is_active=True)
