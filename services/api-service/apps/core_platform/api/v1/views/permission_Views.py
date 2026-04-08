from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api_response import ApiResponse
from apps.core_platform.api.base import BasePlatformAPIView
from apps.core_platform.services.platform_context_service import PlatformContextService
from apps.rbac.api.v1.serializers import PermissionSerializer
from apps.rbac.models import Permission
from apps.rbac.selectors import PermissionSelector
from apps.rbac.services.permission_service import PermissionService


class PlatformContextAPI(BasePlatformAPIView):

    def get(self, request):

        service = PlatformContextService()

        context = service.get_platform_context(request=request)

        return ApiResponse.success(
            data=context,
            message="Platform context retrieved successfully",
            status=status.HTTP_200_OK,
        )


class PlatformPermissionListCreateAPI(BasePlatformAPIView):

    def get(self, request):

        permissions = PermissionSelector.list_all_permissions()

        serializer = PermissionSerializer(permissions, many=True)

        return ApiResponse.success(
            data=serializer.data,
            message="permissions listed successfully",
            status=status.HTTP_200_OK,
        )

    def post(self, request):

        serializer = PermissionSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        permission = PermissionService.create_permission(serializer.validated_data)

        return Response(
            PermissionSerializer(permission).data, status=status.HTTP_201_CREATED
        )


class PlatformPermissionDetailAPI(BasePlatformAPIView):

    def get_object(self, pk):

        return get_object_or_404(Permission, pk=pk)

    def get(self, request, pk):

        permission = self.get_object(pk)

        serializer = PermissionSerializer(permission)

        return Response(serializer.data)

    def patch(self, request, pk):

        permission = self.get_object(pk)

        serializer = PermissionSerializer(permission, data=request.data, partial=True)

        serializer.is_valid(raise_exception=True)

        updated_permission = PermissionService.update_permission(
            permission, serializer.validated_data
        )

        return Response(PermissionSerializer(updated_permission).data)

    def delete(self, request, pk):

        permission = self.get_object(pk)

        PermissionService.delete_permission(permission)

        return Response(status=status.HTTP_204_NO_CONTENT)
