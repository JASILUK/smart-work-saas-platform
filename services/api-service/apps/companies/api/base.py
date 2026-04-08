from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.billing.permissions import ActiveSubscriptionPermission
from apps.companies.permissions import CompanyContextPermission
from apps.rbac.permissions import RolePermission


class BaseCompanyAPIView(APIView):
    permission_classes = [
        IsAuthenticated,
        CompanyContextPermission,
        ActiveSubscriptionPermission,
        RolePermission,
    ]
