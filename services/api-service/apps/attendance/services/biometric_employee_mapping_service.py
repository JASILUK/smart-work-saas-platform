from typing import Any, Dict, Optional
from django.db import transaction
from apps.companies.models import Company, Membership
from apps.attendance.models.biometric_employee_mapping import BiometricEmployeeMapping
from apps.attendance.validators.biometric_employee_mapping_validator import BiometricEmployeeMappingValidator


class BiometricEmployeeMappingService:
    """
    Handles identity synchronization bindings mapping workforce user partitions safely into terminal units.
    """

    @classmethod
    @transaction.atomic
    def create_mapping(cls, *, company: Company, actor: Optional[Membership], validated_data: Dict[str, Any]) -> BiometricEmployeeMapping:
        membership = validated_data["membership"]
        device = validated_data["device"]
        
        # Enforce multi-tenant boundaries
        BiometricEmployeeMappingValidator.validate_tenant_boundary(membership, device)
        validated_data["device_user_id"] = BiometricEmployeeMappingValidator.normalize_device_user_id(validated_data["device_user_id"])

        return BiometricEmployeeMapping.objects.create(
            company=company,
            created_by=actor,
            membership=membership,
            device=device,
            device_user_id=validated_data["device_user_id"],
            is_active=validated_data.get("is_active", True)
        )

    @classmethod
    @transaction.atomic
    def update_mapping(cls, *, mapping: BiometricEmployeeMapping, validated_data: Dict[str, Any]) -> BiometricEmployeeMapping:
        if "device_user_id" in validated_data:
            validated_data["device_user_id"] = BiometricEmployeeMappingValidator.normalize_device_user_id(validated_data["device_user_id"])

        for attr, value in validated_data.items():
            setattr(mapping, attr, value)

        mapping.save()
        return mapping

    @classmethod
    @transaction.atomic
    def activate_mapping(cls, *, mapping: BiometricEmployeeMapping) -> BiometricEmployeeMapping:
        if not mapping.is_active:
            mapping.is_active = True
            mapping.save(update_fields=["is_active", "updated_at"])
        return mapping

    @classmethod
    @transaction.atomic
    def deactivate_mapping(cls, *, mapping: BiometricEmployeeMapping) -> BiometricEmployeeMapping:
        if mapping.is_active:
            mapping.is_active = False
            mapping.save(update_fields=["is_active", "updated_at"])
        return mapping