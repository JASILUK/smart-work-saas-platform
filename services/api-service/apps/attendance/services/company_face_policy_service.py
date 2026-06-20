from django.db import transaction
from apps.companies.models import Company
from apps.attendance.models.company_face_policy import CompanyFaceEnrollmentPolicy


class CompanyFaceEnrollmentPolicyService:
    """
    Coordinates creation, atomic modification loops, and soft-deactivation 
    transactions for company-wide biometric face registration strategies.
    """

    @classmethod
    @transaction.atomic
    def create_policy(cls, *, company: Company, policy_type: str, is_active: bool = True) -> CompanyFaceEnrollmentPolicy:
        """
        Initializes a fresh face policy tracking node inside the database layer.
        Enforces one-to-one tenant uniqueness constraints by deactivating previous policy rows.
        """
        if is_active:
            CompanyFaceEnrollmentPolicy.objects.filter(company=company).update(is_active=False)
            
        return CompanyFaceEnrollmentPolicy.objects.create(
            company=company,
            policy_type=policy_type,
            is_active=is_active
        )

    @classmethod
    @transaction.atomic
    def update_policy(cls, *, instance: CompanyFaceEnrollmentPolicy, validated_data: dict) -> CompanyFaceEnrollmentPolicy:
        """
        Updates an existing configuration statement line item attributes dynamically.
        Deactivates sibling records within the same tenant scope if this instance is flipped to active.
        """
        if validated_data.get("is_active", instance.is_active) and not instance.is_active:
            CompanyFaceEnrollmentPolicy.objects.filter(company=instance.company).update(is_active=False)

        for attr, val in validated_data.items():
            setattr(instance, attr, val)
            
        instance.save()
        return instance

    @classmethod
    @transaction.atomic
    def deactivate_policy(cls, *, instance: CompanyFaceEnrollmentPolicy) -> CompanyFaceEnrollmentPolicy:
        """
        Executes a company-wide soft deactivation of the face registration strategy.
        Bypasses destructive hard-deletes to protect audit logs and operational history tracking.
        """
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        return instance