# rbac/api/v1/views.py

from rest_framework import status
from rest_framework.response import Response

from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse
from apps.rbac.api.v1.serializers import PermissionSerializer, RoleSerializer
from apps.rbac.selectors import PermissionSelector, RoleSelector
from apps.rbac.services.role_service import RoleService


class RoleListCreateAPI(BaseCompanyAPIView):

    required_permissions = {
        "GET": "tenant.role.view",
        "POST": "tenant.role.create",
    }

    def get(self, request):

        roles = RoleSelector.list_company_roles(request.company)

        serializer = RoleSerializer(roles, many=True)

        return ApiResponse.success(data=serializer.data)

    def post(self, request):

        serializer = RoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = RoleService()

        role = service.create_role(
            data=serializer.validated_data, company=request.company
        )

        return ApiResponse.success(
            data=RoleSerializer(role).data,
            status=status.HTTP_201_CREATED,
            message="Role created successfully",
        )


class RoleDetailAPI(BaseCompanyAPIView):

    required_permissions = {
        "GET": "tenant.role.view",
        "PUT": "tenant.role.update",
        "DELETE": "tenant.role.delete",
    }

    def get(self, request, pk):

        role = RoleSelector.get_role(pk, request.company)

        if not role:
            return ApiResponse.error("Role not found", status=404)

        serializer = RoleSerializer(role)

        return ApiResponse.success(data=serializer.data)

    def put(self, request, pk):

        role = RoleSelector.get_role(pk, request.company)

        if not role:
            return ApiResponse.error("Role not found", status=404)

        serializer = RoleSerializer(role, data=request.data)
        serializer.is_valid(raise_exception=True)

        service = RoleService()

        updated_role = service.update_role(role, serializer.validated_data)

        return ApiResponse.success(
            data=RoleSerializer(updated_role).data, message="Role updated successfully"
        )

    def delete(self, request, pk):

        role = RoleSelector.get_role(pk, request.company)

        if not role:
            return ApiResponse.error("Role not found", status=404)

        service = RoleService()

        service.delete_role(role)

        return ApiResponse.success(message="Role deleted successfully")


class TenantPermissionListAPI(BaseCompanyAPIView):

    required_permissions = {"GET": "tenant.role.create"}

    def get(self, request):

        permissions = PermissionSelector.list_tenant_permissions()

        serializer = PermissionSerializer(permissions, many=True)

        return ApiResponse.success(data=serializer.data)
