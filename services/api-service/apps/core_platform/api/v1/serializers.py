from typing import Optional

from rest_framework import serializers

from apps.companies.models import Department
from apps.companies.selectors.Employee_selectors import DepartmentSelector
from apps.core_platform.models import PlatformRole
from apps.rbac.models import Permission


class PlatformRoleSerializer(serializers.ModelSerializer):

    permissions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.filter(scope="platform")
    )

    class Meta:
        model = PlatformRole
        fields = ["id", "name", "permissions"]
