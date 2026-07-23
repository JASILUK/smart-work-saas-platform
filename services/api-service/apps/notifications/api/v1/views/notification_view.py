from apps.notifications.models import NotificationDevice
from rest_framework import status

from rest_framework.views import APIView

from apps.core.api_response import ApiResponse

from apps.companies.api.base import (
    BaseCompanyAPIView,
)

from apps.notifications.services.device_service import (
    DeviceService,
)

from apps.notifications.services.preference_service import (
    PreferenceService,
)

from apps.notifications.api.v1.serializers import (
    NotificationDeviceSerializer,
    RegisterDeviceSerializer,
    DeactivateDeviceSerializer,
    NotificationPreferenceSerializer,
)


class RegisterDeviceView(
    BaseCompanyAPIView
):

    def post(self, request):

        serializer = (
            RegisterDeviceSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        device = (
            DeviceService.register_device(
                user=request.user,
                membership=request.membership,
                **serializer.validated_data,
            )
        )

        return ApiResponse.success(
            message=(
                "Device registered successfully."
            ),
            data={
                "device_id": str(device.id),
            },
            status=status.HTTP_201_CREATED,
        )
    
    


class DeactivateDeviceView(
    BaseCompanyAPIView
):

    def post(self, request):

        serializer = (
            DeactivateDeviceSerializer(
                data=request.data
            )
        )

        serializer.is_valid(
            raise_exception=True
        )

        DeviceService.deactivate_device(
            membership=request.membership,
            device_id=serializer.validated_data[
                "device_id"
            ],
        )

        return ApiResponse.success(
            message=(
                "Device deactivated successfully."
            )
        )




class NotificationPreferenceView(
    BaseCompanyAPIView
):

    def get(self, request):

        preferences = (
            PreferenceService.get_preferences(
                membership=request.membership,
            )
        )

        serializer = (
            NotificationPreferenceSerializer(
                preferences
            )
        )

        return ApiResponse.success(
            data=serializer.data
        )

    def patch(self, request):

        preferences = (
            PreferenceService.update_preferences(
                membership=request.membership,
                data=request.data,
            )
        )

        serializer = (
            NotificationPreferenceSerializer(
                preferences
            )
        )

        return ApiResponse.success(
            message=(
                "Notification preferences updated successfully."
            ),
            data=serializer.data,
        )

class NotificationDeviceListView(
    BaseCompanyAPIView
):

    def get(self, request):

        devices = (
            NotificationDevice.objects
            .filter(
                membership=request.membership
            )
            .order_by("-updated_at")
        )

        serializer = (
            NotificationDeviceSerializer(
                devices,
                many=True,
            )
        )

        return ApiResponse.success(
            data=serializer.data
        )