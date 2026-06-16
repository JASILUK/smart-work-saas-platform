from typing import Any, Dict, Optional
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.attendance.models import AttendancePolicy
from apps.attendance.selectors.attendance_policy_selector import AttendancePolicySelector


class AttendancePolicyService:
    """
    Orchestration service handling write operations, lifecycle state transitions,
    and policy defaults initialization for company-level Attendance Configurations.
    """

    # =====================================================
    # GET OR CREATE DEFAULT POLICY
    # =====================================================

    @staticmethod
    @transaction.atomic
    def get_or_create_default_policy(*, company: Any) -> AttendancePolicy:
        """
        Ensures a company tenant workspace always maps to a valid interpretation rule set.
        Returns the existing active configuration profile, or safely instantiates a fresh row 
        populated with the foundational model field defaults.
        """
        policy = AttendancePolicySelector.get_by_company(company=company)
        if policy:
            return policy

        # Handle fallback check for an inactive policy instance to prevent OneToOne unique clashes
        policy = AttendancePolicy.objects.filter(company=company).first()
        if policy:
            policy.is_active = True
            policy.save(update_fields=["is_active"])
            return policy

        return AttendancePolicy.objects.create(
            company=company,
            is_active=True
        )

    # =====================================================
    # CREATE POLICY
    # =====================================================

    @staticmethod
    @transaction.atomic
    def create_policy(*, company: Any, created_data: Dict[str, Any]) -> AttendancePolicy:
        """
        Registers a fresh, dedicated attendance interpretation roster matrix for a company tenant.
        Raises a validation error if a configuration rule set has already been instantiated.
        """
        if AttendancePolicy.objects.filter(company=company).exists():
            raise ValidationError("An attendance policy configuration already exists for this company.")

        return AttendancePolicy.objects.create(
            company=company,
            **created_data
        )

    # =====================================================
    # UPDATE POLICY
    # =====================================================

    @staticmethod
    @transaction.atomic
    def update_policy(*, company: Any, validated_data: Dict[str, Any]) -> AttendancePolicy:
        """
        Updates an active policy schema configuration using targeted partial patch payloads.
        Maintains performance optimization by executing mutations exclusively via update_fields.
        """
        policy = AttendancePolicySelector.get_by_company(company=company)
        if not policy:
            raise ValidationError("No active attendance policy configuration found for this company to update.")

        update_fields = []
        for field, value in validated_data.items():
            if hasattr(policy, field):
                setattr(policy, field, value)
                update_fields.append(field)

        if update_fields:
            if hasattr(policy, "modified"):
                update_fields.append("modified")
            policy.save(update_fields=update_fields)

        return policy

    # =====================================================
    # ACTIVATE POLICY
    # =====================================================

    @staticmethod
    @transaction.atomic
    def activate_policy(*, company: Any) -> AttendancePolicy:
        """
        Enables structural tracking parameters by asserting the operational enforcement flag toggle.
        """
        policy = AttendancePolicy.objects.filter(company=company).first()
        if not policy:
            raise ValidationError("No attendance policy configuration exists for this company.")

        if not policy.is_active:
            policy.is_active = True
            update_fields = ["is_active"]
            if hasattr(policy, "modified"):
                update_fields.append("modified")
            policy.save(update_fields=update_fields)

        return policy

    # =====================================================
    # DEACTIVATE POLICY
    # =====================================================

    @staticmethod
    @transaction.atomic
    def deactivate_policy(*, company: Any) -> AttendancePolicy:
        """
        Temporarily flags an active policy configuration record as inactive, pausing downstream 
        auto-absenteeism calculations or overtime computation logic.
        """
        policy = AttendancePolicySelector.get_by_company(company=company)
        if not policy:
            raise ValidationError("No active attendance policy configuration found to deactivate.")

        policy.is_active = False
        update_fields = ["is_active"]
        if hasattr(policy, "modified"):
            update_fields.append("modified")
            
        policy.save(update_fields=update_fields)
        return policy

    # =====================================================
    # RESET TO DEFAULTS
    # =====================================================

    @staticmethod
    @transaction.atomic
    def reset_to_defaults(*, company: Any) -> AttendancePolicy:
        """
        Restores compliance thresholds back to corporate base line parameters,
        wiping out customized tenant override variables.
        """
        policy = AttendancePolicy.objects.filter(company=company).first()
        if not policy:
            raise ValidationError("No attendance policy configuration exists for this company to reset.")

        policy.required_work_minutes = 480
        policy.half_day_below_minutes = 240
        policy.late_after_minutes = 10
        policy.early_exit_before_minutes = 30
        policy.overtime_enabled = False
        policy.overtime_after_minutes = 480
        policy.auto_absent_if_no_checkin = True
        policy.count_weekend_as_overtime = False
        policy.attendance_regularization_enabled = True
        policy.is_active = True

        update_fields = [
            "required_work_minutes",
            "half_day_below_minutes",
            "late_after_minutes",
            "early_exit_before_minutes",
            "overtime_enabled",
            "overtime_after_minutes",
            "auto_absent_if_no_checkin",
            "count_weekend_as_overtime",
            "attendance_regularization_enabled",
            "is_active",
        ]

        if hasattr(policy, "modified"):
            update_fields.append("modified")

        policy.save(update_fields=update_fields)
        return policy