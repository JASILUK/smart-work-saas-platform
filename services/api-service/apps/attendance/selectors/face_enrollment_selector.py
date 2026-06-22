from typing import Optional
from django.db.models import QuerySet, Q
from apps.companies.models import Company, Membership
from apps.attendance.models.face_enrollment import FaceEnrollment, EnrollmentStatusChoices

class FaceEnrollmentSelector:
    """
    Provides optimized lookup methods for face enrollment records, using 
    pre-fetches to prevent N+1 queries during serialization sweeps.
    """
    
    @classmethod
    def get_queryset(cls) -> QuerySet[FaceEnrollment]:
        """
        Base optimized queryset capturing critical relational database joins up-front.
        """
        return FaceEnrollment.objects.select_related(
            "company", 
            "membership__user", 
            "approved_by__user", 
            "revoked_by__user"
        )

    @classmethod
    def get_by_id(
        cls, *, enrollment_id: int, company: Company, membership: Optional[Membership] = None
    ) -> Optional[FaceEnrollment]:
        """
        Resolves a single unique face template tracking configuration safely bounded by tenant scope.
        Optionally handles employee self-service constraints to isolate row-level identity lookups.
        """
        queryset = cls.get_queryset().filter(id=enrollment_id, company=company)
        
        if membership is not None:
            queryset = queryset.filter(membership=membership)
            
        return queryset.first()

    @classmethod
    def list_company_enrollments(
        cls, *, company: Company, membership: Optional[Membership] = None
    ) -> QuerySet[FaceEnrollment]:
        """
        Lists all registration profiles logged across a specific company workspace context.
        Applies row-level ownership isolation if a membership context modifier parameter is supplied.
        """
        queryset = cls.get_queryset().filter(company=company)
        
        if membership is not None:
            queryset = queryset.filter(membership=membership)
            
        return queryset
    
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
    def get_active_or_pending_enrollment(cls, company: Company, membership: Membership) -> Optional[FaceEnrollment]:
        """
        Synthesized entry point matching dashboard orchestration contracts securely.
        Prioritizes an APPROVED profile, falling back to a PENDING record if available.
        """
        enrollments = cls.get_queryset().filter(
            company=company,
            membership=membership,
            status__in=[EnrollmentStatusChoices.APPROVED, EnrollmentStatusChoices.PENDING]
        )
        # Prioritize APPROVED over PENDING
        return sorted(enrollments, key=lambda x: x.status == EnrollmentStatusChoices.APPROVED, reverse=True)[0] if enrollments else None

    @classmethod
    def get_pending_enrollments(cls, company: Company) -> QuerySet[FaceEnrollment]:
        """
        Returns all entries awaiting HR administrative action.
        """
        return cls.get_queryset().filter(
            company=company,
            status=EnrollmentStatusChoices.PENDING
        ).order_by("created_at")