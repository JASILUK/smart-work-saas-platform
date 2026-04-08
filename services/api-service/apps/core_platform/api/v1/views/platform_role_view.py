from rest_framework import status

from apps.core.api_response import ApiResponse
from apps.core.exceptions import ApplicationError
from apps.core_platform.api.base import BasePlatformAPIView
from apps.core_platform.api.v1.serializers import PlatformRoleSerializer
from apps.core_platform.selectors import PlatformRoleSelector
from apps.core_platform.services.platform_role_service import PlatformRoleService


class PlatformRoleListCreateAPI(BasePlatformAPIView):

    required_permissions = {"GET": "platform.role.view", "POST": "platform.role.create"}

    def get(self, request):

        roles = PlatformRoleSelector.list_roles()

        serializer = PlatformRoleSerializer(roles, many=True)

        return ApiResponse.success(
            data=serializer.data, message="Platform roles retrieved"
        )

    def post(self, request):

        serializer = PlatformRoleSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        role = PlatformRoleService.create_role(serializer.validated_data)

        return ApiResponse.success(
            data=PlatformRoleSerializer(role).data,
            message="Platform role created",
            status=status.HTTP_201_CREATED,
        )


class PlatformRoleDetailAPI(BasePlatformAPIView):

    required_permissions = {
        "GET": "platform.role.view",
        "PATCH": "platform.role.update",
        "DELETE": "platform.role.delete",
    }

    def get_object(self, pk):

        role = PlatformRoleSelector.get_role(pk)

        if not role:
            raise ApplicationError(message="Platform role not found")

        return role

    def get(self, request, pk):

        role = self.get_object(pk)

        serializer = PlatformRoleSerializer(role)

        return ApiResponse.success(serializer.data)

    def patch(self, request, pk):

        role = self.get_object(pk)

        serializer = PlatformRoleSerializer(role, data=request.data, partial=True)

        serializer.is_valid(raise_exception=True)

        role = PlatformRoleService.update_role(role, serializer.validated_data)

        return ApiResponse.success(
            PlatformRoleSerializer(role).data, message="Platform role updated"
        )

    def delete(self, request, pk):

        role = self.get_object(pk)

        PlatformRoleService.delete_role(role)

        return ApiResponse.success(
            message="Platform role deleted", status=status.HTTP_204_NO_CONTENT
        )
