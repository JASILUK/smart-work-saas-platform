from typing import Optional
from django.db.models import QuerySet
from apps.companies.models import Company, Membership
from apps.attendance.models.face_enrollment import FaceEnrollment, EnrollmentStatusChoices


class FaceEnrollmentSelector:
    """
    Provides optimized lookup methods for face enrollment records, using pre-fetches to prevent N+1 queries.
    """
    @classmethod
    def get_queryset(cls) -> QuerySet[FaceEnrollment]:
        return FaceEnrollment.objects.select_related(
            "company", 
            "membership__user", 
            "approved_by__user", 
            "revoked_by__user"
        )

    @classmethod
    def get_by_id(cls, enrollment_id: int, company: Company) -> Optional[FaceEnrollment]:
        """
        Resolves a single unique face template tracking configuration safely bounded by tenant scope.
        """
        return cls.get_queryset().filter(id=enrollment_id, company=company).first()

    @classmethod
    def list_company_enrollments(cls, company: Company) -> QuerySet[FaceEnrollment]:
        """
        Lists all registration profiles logged across a specific company workspace context.
        """
        return cls.get_queryset().filter(company=company)

    @classmethod
    def list_membership_enrollments(cls, company: Company, membership: Membership) -> QuerySet[FaceEnrollment]:
        """
        Returns the entire historical registration trail logged by a single employee profile.
        """
        return cls.get_queryset().filter(company=company, membership=membership)

    @classmethod
    def get_active_enrollment(cls, company: Company, membership: Membership) -> Optional[FaceEnrollment]:
        """
        Returns the single active approved biometric signature used for production sign-in verifications.
        """
        return cls.get_queryset().filter(
            company=company,
            membership=membership,
            status=EnrollmentStatusChoices.APPROVED
        ).first()

    @classmethod
    def get_pending_enrollments(cls, company: Company) -> QuerySet[FaceEnrollment]:
        """
        Returns all entries awaiting HR administrative action.
        """
        return cls.get_queryset().filter(
            company=company,
            status=EnrollmentStatusChoices.PENDING
        ).order_by("created_at")