from django.db import transaction
from apps.companies.models import Company, Membership
from apps.attendance.models.employee_attendance_override import EmployeeAttendanceOverride
from apps.attendance.validators.attendance_access_validator import AttendanceAccessValidator


class EmployeeAttendanceOverrideService:
    """
    Handles transactions for individual employee configuration exceptions.
    """
    @classmethod
    @transaction.atomic
    def create_override(cls, *, company: Company, membership: Membership, validated_data: dict) -> EmployeeAttendanceOverride:
        method_ids = [m.id for m in validated_data.pop("allowed_methods", [])]
        location_ids = [l.id for l in validated_data.pop("allowed_locations", [])]

        if validated_data.get("is_active", True):
            AttendanceAccessValidator.validate_override_uniqueness(membership=membership)
        AttendanceAccessValidator.validate_method_and_locations(method_ids, location_ids, company)

        override = EmployeeAttendanceOverride(company=company, membership=membership, **validated_data)
        override.save()
        override.allowed_methods.set(method_ids)
        override.allowed_locations.set(location_ids)
        return override

    @classmethod
    @transaction.atomic
    def update_override(cls, *, instance: EmployeeAttendanceOverride, validated_data: dict) -> EmployeeAttendanceOverride:
        method_objs = validated_data.pop("allowed_methods", None)
        location_objs = validated_data.pop("allowed_locations", None)

        for attr, val in validated_data.items():
            setattr(instance, attr, val)

        if instance.is_active:
            AttendanceAccessValidator.validate_override_uniqueness(membership=instance.membership, exclude_id=instance.id)

        m_ids = [m.id for m in method_objs] if method_objs is not None else list(instance.allowed_methods.values_list("id", flat=True))
        l_ids = [l.id for l in location_objs] if location_objs is not None else list(instance.allowed_locations.values_list("id", flat=True))

        AttendanceAccessValidator.validate_method_and_locations(m_ids, l_ids, instance.company)
        instance.save()

        if method_objs is not None:
            instance.allowed_methods.set(method_objs)
        if location_objs is not None:
            instance.allowed_locations.set(location_objs)

        return instance

    @classmethod
    @transaction.atomic
    def remove_override(cls, *, instance: EmployeeAttendanceOverride) -> None:
        """
        Completely hard-deletes an override statement since overrides represent transient behavioral edge-cases.
        """
        instance.delete()