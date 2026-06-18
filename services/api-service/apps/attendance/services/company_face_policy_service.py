from django.db import transaction
from apps.companies.models import Company
from apps.attendance.models.company_face_policy import CompanyFaceEnrollmentPolicy


class CompanyFaceEnrollmentPolicyService:
    """
    Manages configuration transactions for company face registration rules.
    """
    @classmethod
    @transaction.atomic
    def create_policy(cls, *, company: Company, policy_type: str, is_active: bool = True) -> CompanyFaceEnrollmentPolicy:
        # Enforce uniqueness by turning off previous rules before initializing a new one
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
        if validated_data.get("is_active", instance.is_active) and not instance.is_active:
            CompanyFaceEnrollmentPolicy.objects.filter(company=instance.company).update(is_active=False)

        for attr, val in validated_data.items():
            setattr(instance, attr, val)
            
        instance.save()
        return instance