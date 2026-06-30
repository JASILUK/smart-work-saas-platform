from django.db.models import QuerySet
from apps.companies.models import Company, Membership

class HREmployeeHeaderSelector:
    """
    Resolves corporate membership properties and user metadata contexts
    for an individual employee in a single relational join database pass.
    """

    @classmethod
    def get_employee_header(cls, *, company: Company, membership_id: int) -> Membership:
        """
        Retrieves the base corporate employee identity details.
        """
        return Membership.objects.select_related(
            "user",
            "department",
            "role"
        ).get(id=membership_id, company=company)