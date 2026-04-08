from rest_framework.permissions import BasePermission

from apps.companies.models import Membership


class CompanyContextPermission(BasePermission):

    def has_permission(self, request, view):

        company_id = request.headers.get("X-Company-ID")

        if not company_id:
            return False

        membership = (
            Membership.objects.select_related("company", "role")
            .prefetch_related("role__permissions")
            .filter(user=request.user, company_id=company_id, is_active=True)
            .first()
        )

        if membership is None:
            return False

        request.company = membership.company
        request.membership = membership

        return True
