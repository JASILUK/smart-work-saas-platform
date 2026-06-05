from django.utils import timezone

from apps.core.exceptions import ApplicationError

from apps.notifications.models import (
    NotificationDevice,
)


class DeviceService:

    # =====================================================
    # REGISTER DEVICE
    # =====================================================

    @staticmethod
    def register_device(
        *,
        user,
        membership,
        device_id,
        token,
        platform,
        device_name=None,
    ):

        device_id = (device_id or "").strip()

        token = (token or "").strip()

        platform = (platform or "").strip()

        device_name = (
            (device_name or "").strip()
            or "Unknown Device"
        )

        # =================================================
        # VALIDATION
        # =================================================

        if not device_id:

            raise ApplicationError(
                "Device ID is required."
            )

        if not token:

            raise ApplicationError(
                "Device token is required."
            )

        if len(token) < 20:

            raise ApplicationError(
                "Invalid device token."
            )

        if not platform:

            raise ApplicationError(
                "Platform is required."
            )

        # =================================================
        # DEACTIVATE DUPLICATE TOKENS
        # =================================================

        NotificationDevice.objects.filter(
            token=token,
        ).exclude(
            membership=membership,
            device_id=device_id,
        ).update(
            is_active=False,
            updated_at=timezone.now(),
        )

        # =================================================
        # CREATE OR UPDATE DEVICE
        # =================================================

        device, _ = (
            NotificationDevice.objects.update_or_create(
                membership=membership,
                device_id=device_id,
                defaults={
                    "user": user,
                    "token": token,
                    "platform": platform,
                    "device_name": device_name,
                    "is_active": True,
                    "last_seen_at": timezone.now(),
                },
            )
        )

        return device

    # =====================================================
    # DEACTIVATE DEVICE
    # =====================================================

    @staticmethod
    def deactivate_device(
        *,
        membership,
        device_id,
    ):

        device_id = (
            (device_id or "").strip()
        )

        if not device_id:

            raise ApplicationError(
                "Device ID is required."
            )

        try:

            device = (
                NotificationDevice.objects.get(
                    membership=membership,
                    device_id=device_id,
                )
            )

        except NotificationDevice.DoesNotExist:

            raise ApplicationError(
                "Device not found."
            )

        device.is_active = False

        device.last_seen_at = (
            timezone.now()
        )

        device.save(
            update_fields=[
                "is_active",
                "last_seen_at",
                "updated_at",
            ]
        )

        return device