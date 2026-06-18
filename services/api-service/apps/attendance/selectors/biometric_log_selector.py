from typing import Optional
from django.db.models import QuerySet
from apps.companies.models import Company, Membership
from apps.attendance.models.biometric_device import BiometricDevice
from apps.attendance.models.biometric_log import BiometricLog, ProcessingStatusChoices


class BiometricLogSelector:
    """
    Optimized data access selectors for Biometric Device Logs.
    """
    @classmethod
    def get_queryset(cls) -> QuerySet[BiometricLog]:
        return BiometricLog.objects.select_related(
            "device", 
            "membership__user"
        )

    @classmethod
    def get_by_id(cls, *, log_id: int, company: Company) -> Optional[BiometricLog]:
        return cls.get_queryset().filter(id=log_id, company=company).first()

    @classmethod
    def get_company_logs(cls, *, company: Company) -> QuerySet[BiometricLog]:
        return cls.get_queryset().filter(company=company)

    @classmethod
    def get_pending_logs(cls, *, company: Company) -> QuerySet[BiometricLog]:
        return cls.get_company_logs(company=company).filter(processing_status=ProcessingStatusChoices.PENDING)

    @classmethod
    def get_failed_logs(cls, *, company: Company) -> QuerySet[BiometricLog]:
        return cls.get_company_logs(company=company).filter(processing_status=ProcessingStatusChoices.FAILED)

    @classmethod
    def get_logs_by_batch(cls, *, company: Company, batch_id: str) -> QuerySet[BiometricLog]:
        return cls.get_company_logs(company=company).filter(sync_batch_id=batch_id)

    @classmethod
    def get_logs_for_membership(cls, *, company: Company, membership: Membership) -> QuerySet[BiometricLog]:
        return cls.get_company_logs(company=company).filter(membership=membership)

    @classmethod
    def get_logs_for_device(cls, *, company: Company, device: BiometricDevice) -> QuerySet[BiometricLog]:
        return cls.get_company_logs(company=company).filter(device=device)

    @classmethod
    def find_duplicate(cls, *, company: Company, device: BiometricDevice, device_log_id: str) -> Optional[BiometricLog]:
        """
        Checks for existing transaction duplicates based on hardware transaction logs indicators fields.
        """
        if not device_log_id or not device:
            return None
        return BiometricLog.objects.filter(
            company=company, 
            device=device, 
            device_log_id=device_log_id
        ).first()