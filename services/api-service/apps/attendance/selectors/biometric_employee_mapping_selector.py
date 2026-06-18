from typing import Optional
from django.db.models import QuerySet
from apps.companies.models import Company, Membership
from apps.attendance.models.biometric_device import BiometricDevice
from apps.attendance.models.biometric_employee_mapping import BiometricEmployeeMapping


class BiometricEmployeeMappingSelector:
    """
    Optimized data access selectors for Biometric Employee Identity Mappings.
    """
    @classmethod
    def get_queryset(cls) -> QuerySet[BiometricEmployeeMapping]:
        return BiometricEmployeeMapping.objects.select_related(
            "company",
            "membership__user",
            "device",
            "created_by__user"
        )

    @classmethod
    def get_by_id(cls, *, mapping_id: int, company: Company) -> Optional[BiometricEmployeeMapping]:
        return cls.get_queryset().filter(id=mapping_id, company=company).first()

    @classmethod
    def get_company_mappings(cls, *, company: Company) -> QuerySet[BiometricEmployeeMapping]:
        return cls.get_queryset().filter(company=company)

    @classmethod
    def get_employee_mappings(cls, *, company: Company, membership: Membership) -> QuerySet[BiometricEmployeeMapping]:
        return cls.get_company_mappings(company=company).filter(membership=membership)

    @classmethod
    def get_device_mappings(cls, *, company: Company, device: BiometricDevice) -> QuerySet[BiometricEmployeeMapping]:
        return cls.get_company_mappings(company=company).filter(device=device)

    @classmethod
    def get_active_mapping(cls, *, company: Company, membership: Membership, device: BiometricDevice) -> Optional[BiometricEmployeeMapping]:
        return cls.get_company_mappings(company=company).filter(
            membership=membership,
            device=device,
            is_active=True
        ).first()

    @classmethod
    def find_by_device_identity(cls, *, company: Company, device: BiometricDevice, device_user_id: str) -> Optional[BiometricEmployeeMapping]:
        """
        Matches a raw string signature captured from incoming check-in data streams back onto an assigned employee identity.
        """
        return cls.get_company_mappings(company=company).filter(
            device=device,
            device_user_id=device_user_id,
            is_active=True
        ).first()