from typing import Any, Dict
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.attendance.models import Shift, EmployeeShiftAssignment, CompanyWorkSchedule
from apps.attendance.selectors.shift_selector import ShiftSelector


class ShiftService:
    """
    Service class handling all write operations, business rules, and state transitions
    for the Shift module. Acts as the single source of truth for shift mutations.
    """

    # =====================================================
    # CREATE SHIFT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def create_shift(*, company: Any, validated_data: Dict[str, Any]) -> Shift:
        """
        Creates a new shift structure inside a tenant workspace.
        Enforces cross-field validations, configuration consistency, and uniqueness boundaries.
        """
        name: str = validated_data.get("name", "").strip()
        is_default: bool = validated_data.pop("is_default", False)

        # 1. Enforce unique shift naming boundaries inside the company tenant
        if ShiftSelector.exists_with_name(company=company, name=name):
            raise ValidationError("Shift name already exists.")

        # 2. Initialize database instance mapping parameters directly
        shift = Shift.objects.create(company=company, **validated_data)

        # 3. Handle default company configurations atomically via CompanyWorkSchedule relation
        if is_default:
            ShiftService.set_default_shift(shift=shift)

        return shift

    # =====================================================
    # UPDATE SHIFT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def update_shift(*, shift: Shift, validated_data: Dict[str, Any]) -> Shift:
        """
        Updates an existing shift definition safely using updated_fields tracking maps.
        Re-validates all business rules against modified inputs.
        """
        company = shift.company
        name: str = validated_data.get("name", shift.name).strip()
        is_default: bool = validated_data.pop("is_default", False)

        # 1. Validate name collisions excluding the current record instance
        if name != shift.name and ShiftSelector.exists_with_name(company=company, name=name, exclude_id=shift.id):
            raise ValidationError("Shift name already exists.")

        # 2. Apply changed values to fields dynamically and save efficiently
        update_fields = []
        for field, value in validated_data.items():
            if hasattr(shift, field):
                setattr(shift, field, value)
                update_fields.append(field)

        if update_fields:
            if hasattr(shift, "modified"):
                update_fields.append("modified")
            shift.save(update_fields=update_fields)

        # 3. Handle changing default shift contexts
        if is_default:
            ShiftService.set_default_shift(shift=shift)

        return shift

    # =====================================================
    # ACTIVATE SHIFT
    # =====================================================

    @staticmethod
    def activate_shift(*, shift: Shift) -> Shift:
        """
        Activates an inactive shift configuration. 
        Acts as a no-op transaction if the shift is already active.
        """
        if shift.is_active:
            return shift

        shift.is_active = True
        update_fields = ["is_active"]
        
        if hasattr(shift, "modified"):
            update_fields.append("modified")
            
        shift.save(update_fields=update_fields)
        return shift

    # =====================================================
    # DEACTIVATE SHIFT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def deactivate_shift(*, shift: Shift) -> Shift:
        """
        Deactivates an active shift configuration.
        Validates active employee assignments and system defaults before saving changes.
        """
        company = shift.company

        # 1. Prevent deactivation if this instance represents the system fallback schedule
        default_shift = ShiftSelector.get_default_shift(company=company)
        if default_shift and default_shift.id == shift.id:
            raise ValidationError("Default shifts cannot be deactivated.")

        # 2. Check for active employee shift assignments using the ORM layer
        has_active_assignments = EmployeeShiftAssignment.objects.filter(
            shift=shift,
            is_active=True
        ).exists()
        
        if has_active_assignments:
            raise ValidationError("Assigned shifts cannot be deactivated.")

        shift.is_active = False
        update_fields = ["is_active"]
        
        if hasattr(shift, "modified"):
            update_fields.append("modified")
            
        shift.save(update_fields=update_fields)
        return shift

    # =====================================================
    # SET DEFAULT SHIFT
    # =====================================================

    @staticmethod
    @transaction.atomic
    def set_default_shift(*, shift: Shift) -> Shift:
        """
        Sets a specific shift as the company default inside CompanyWorkSchedule. 
        Automatically activates the shift if it was previously deactivated.
        """
        company = shift.company

        # 1. Activate the shift automatically if it is currently marked inactive
        if not shift.is_active:
            ShiftService.activate_shift(shift=shift)

        # 2. Retrieve or instantiate the one-to-one company schedule record context
        work_schedule, created = CompanyWorkSchedule.objects.get_or_create(
            company=company,
            defaults={
                "work_start_time": shift.start_time,
                "work_end_time": shift.end_time,
                "timezone": "UTC",
                "country": "Unknown"
            }
        )

        # 3. Update the foreign key pointer target to point directly to this shift
        work_schedule.default_shift = shift
        
        update_fields = ["default_shift"]
        if hasattr(work_schedule, "modified"):
            update_fields.append("modified")
            
        work_schedule.save(update_fields=update_fields)
        return shift