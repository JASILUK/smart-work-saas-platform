from typing import Optional
from django.db.models import QuerySet
from apps.companies.models import Company
from apps.attendance.models.biometric_device import BiometricDevice, BiometricSyncMode


class BiometricDeviceSelector:
    """
    Optimized data access selectors for Biometric Device configurations.
    """
    @classmethod
    def get_queryset(cls) -> QuerySet[BiometricDevice]:
        return BiometricDevice.objects.select_related("company")

    @classmethod
    def get_by_id(cls, *, device_id: int, company: Company) -> Optional[BiometricDevice]:
        return cls.get_queryset().filter(id=device_id, company=company).first()

    @classmethod
    def get_company_devices(cls, *, company: Company) -> QuerySet[BiometricDevice]:
        return cls.get_queryset().filter(company=company)

    @classmethod
    def get_active_devices(cls, *, company: Company) -> QuerySet[BiometricDevice]:
        return cls.get_company_devices(company=company).filter(is_active=True)

    @classmethod
    def get_pull_devices(cls) -> QuerySet[BiometricDevice]:
        """
        Fetches all network-reachable PULL terminals to coordinate automated background ingestion processing.
        """
        return cls.get_queryset().filter(is_active=True, sync_mode=BiometricSyncMode.PULL)

    @classmethod
    def get_by_serial(cls, *, serial_number: str, company: Company) -> Optional[BiometricDevice]:
        return cls.get_company_devices(company=company).filter(serial_number=serial_number).first()

    @classmethod
    def get_by_device_code(cls, *, device_code: str, company: Company) -> Optional[BiometricDevice]:
        return cls.get_company_devices(company=company).filter(device_code=device_code).first()