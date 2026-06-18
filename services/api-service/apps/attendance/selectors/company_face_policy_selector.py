from typing import Optional
from apps.companies.models import Company
from apps.attendance.models.company_face_policy import CompanyFaceEnrollmentPolicy


class CompanyFaceEnrollmentPolicySelector:
    """
    Optimized data access selectors for Company Face Enrollment Policies.
    """
    @classmethod
    def get_queryset(cls):
        return CompanyFaceEnrollmentPolicy.objects.select_related("company")

    @classmethod
    def get_active_policy(cls, company: Company) -> Optional[CompanyFaceEnrollmentPolicy]:
        """
        Fetches the active face enrollment configuration policy for a specific tenant company workspace.
        """
        return cls.get_queryset().filter(company=company, is_active=True).first()