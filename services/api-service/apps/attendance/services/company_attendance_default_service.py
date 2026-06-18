from typing import List
from django.db import transaction
from apps.companies.models import Company
from apps.attendance.models.company_attendance_default import CompanyAttendanceDefault
from apps.attendance.validators.attendance_access_validator import AttendanceAccessValidator


class CompanyAttendanceDefaultService:
    """
    Handles transactions for company-wide default configurations.
    """
    @classmethod
    @transaction.atomic
    def create_default(cls, *, company: Company, method_ids: List[int], location_ids: List[int], validation_mode: str, is_active: bool = True) -> CompanyAttendanceDefault:
        if is_active:
            AttendanceAccessValidator.validate_default_uniqueness(company=company)
        AttendanceAccessValidator.validate_method_and_locations(method_ids, location_ids, company)

        instance = CompanyAttendanceDefault.objects.create(
            company=company,
            validation_mode=validation_mode,
            is_active=is_active
        )
        instance.allowed_methods.set(method_ids)
        instance.allowed_locations.set(location_ids)
        return instance

    @classmethod
    @transaction.atomic
    def update_default(cls, *, instance: CompanyAttendanceDefault, validated_data: dict) -> CompanyAttendanceDefault:
        method_ids = validated_data.get("allowed_methods")
        location_ids = validated_data.get("allowed_locations")
        is_active = validated_data.get("is_active", instance.is_active)

        if is_active and not instance.is_active:
            AttendanceAccessValidator.validate_default_uniqueness(company=instance.company, exclude_id=instance.id)

        if method_ids is not None or location_ids is not None:
            m_ids = [m.id for m in method_ids] if method_ids is not None else list(instance.allowed_methods.values_list("id", flat=True))
            l_ids = [l.id for l in location_ids] if location_ids is not None else list(instance.allowed_locations.values_list("id", flat=True))
            AttendanceAccessValidator.validate_method_and_locations(m_ids, l_ids, instance.company)

        if "validation_mode" in validated_data:
            instance.validation_mode = validated_data["validation_mode"]
        instance.is_active = is_active
        instance.save()

        if method_ids is not None:
            instance.allowed_methods.set(method_ids)
        if location_ids is not None:
            instance.allowed_locations.set(location_ids)

        return instance