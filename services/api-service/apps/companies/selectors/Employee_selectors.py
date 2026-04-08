from django.shortcuts import get_object_or_404

from apps.companies.models import Company, Membership


def get_pending_company_by_owner(user):
    return Company.objects.filter(owner=user, status=Company.Status.PENDING).first()


class EmployeeSelector:

    @staticmethod
    def list_company_employees(company):

        return Membership.objects.filter(company=company).select_related("user", "role")

    @staticmethod
    def get_employee(company, employee_id):

        return get_object_or_404(
            Membership.objects.select_related("user", "role"),
            id=employee_id,
            company=company,
        )
