from typing import Any, Dict
from django.db import transaction
from django.utils import timezone
from apps.companies.models import Company
from apps.attendance.models.biometric_device import BiometricDevice
from apps.attendance.validators.biometric_device_validator import BiometricDeviceValidator


class BiometricDeviceService:
    """
    Manages structural configuration workflows and lifecycle updates for biometric hardware terminals.
    """

    @classmethod
    @transaction.atomic
    def create_device(cls, *, company: Company, validated_data: Dict[str, Any]) -> BiometricDevice:
        validated_data["device_code"] = BiometricDeviceValidator.normalize_device_code(validated_data["device_code"])
        BiometricDeviceValidator.validate_device_networking(validated_data)
        BiometricDeviceValidator.validate_timezone_string(validated_data.get("timezone", "Asia/Kolkata"))

        return BiometricDevice.objects.create(company=company, **validated_data)

    @classmethod
    @transaction.atomic
    def update_device(cls, *, device: BiometricDevice, validated_data: Dict[str, Any]) -> BiometricDevice:
        if "device_code" in validated_data:
            validated_data["device_code"] = BiometricDeviceValidator.normalize_device_code(validated_data["device_code"])

        # Merge new changes into current runtime records to evaluate network configuration changes
        merged_context = {
            "sync_mode": validated_data.get("sync_mode", device.sync_mode),
            "ip_address": validated_data.get("ip_address", device.ip_address),
            "port": validated_data.get("port", device.port)
        }
        BiometricDeviceValidator.validate_device_networking(merged_context)

        if "timezone" in validated_data:
            BiometricDeviceValidator.validate_timezone_string(validated_data["timezone"])

        for attr, value in validated_data.items():
            setattr(device, attr, value)

        device.save()
        return device

    @classmethod
    @transaction.atomic
    def activate_device(cls, *, device: BiometricDevice) -> BiometricDevice:
        if not device.is_active:
            device.is_active = True
            device.save(update_fields=["is_active", "updated_at"])
        return device

    @classmethod
    @transaction.atomic
    def deactivate_device(cls, *, device: BiometricDevice) -> BiometricDevice:
        """ Soft-deactivates the terminal configuration without breaking historic partition links. """
        if device.is_active:
            device.is_active = False
            device.save(update_fields=["is_active", "updated_at"])
        return device

    @classmethod
    @transaction.atomic
    def mark_synced(cls, *, device: BiometricDevice) -> BiometricDevice:
        """ Updates synchronization tracking marks to provide real-time connection telemetry checks. """
        device.last_synced_at = timezone.now()
        device.save(update_fields=["last_synced_at", "updated_at"])
        return device