import django.utils.timezone as timezone
from typing import List, Optional
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.companies.models import Company, Membership
from apps.attendance.models.company_face_policy import PolicyTypeChoices
from apps.attendance.models.face_enrollment import FaceEnrollment, EnrollmentStatusChoices, EnrollmentSourceChoices
from apps.attendance.validators.face_enrollment_validator import FaceEnrollmentValidator
from apps.attendance.selectors.company_face_policy_selector import CompanyFaceEnrollmentPolicySelector
from apps.attendance.selectors.face_enrollment_selector import FaceEnrollmentSelector


class FaceEnrollmentService:
    """
    Coordinates creation, lifecycle transitions, and deactivation workflows for biometric face signatures.
    """

    @classmethod
    @transaction.atomic
    def submit_self_enrollment(cls, *, company: Company, membership: Membership, embedding: List[float]) -> FaceEnrollment:
        """
        Handles employee self-service enrollment requests submitted from user terminals.
        Applies auto-approval rules or assigns a pending status based on company policy settings.
        """
        FaceEnrollmentValidator.validate_embedding_structure(embedding)
        
        # Resolve active policy rules parameters
        policy = CompanyFaceEnrollmentPolicySelector.get_active_policy(company=company)
        if not policy:
            # Safe system baseline fallback definition defaults
            policy_type = PolicyTypeChoices.SELF_WITH_APPROVAL
        else:
            policy_type = policy.policy_type

        if policy_type == PolicyTypeChoices.HR_ONLY:
            raise DjangoValidationError(_("Self-enrollment is restricted. Registrations must be initiated directly by an HR administrator."))

        # Initialize the baseline template record entry
        enrollment = FaceEnrollment.objects.create(
            company=company,
            membership=membership,
            enrollment_source=EnrollmentSourceChoices.EMPLOYEE,
            embedding=embedding,
            status=EnrollmentStatusChoices.PENDING,
            liveness_verified=True  # Assumes frontend verification mechanisms cleared device inputs
        )

        # Apply auto-approval workflow if company settings allow
        if policy_type == PolicyTypeChoices.SELF_ONLY:
            cls.approve_enrollment(enrollment=enrollment, actor=None)

        return enrollment

    @classmethod
    @transaction.atomic
    def hr_enroll_employee(cls, *, company: Company, target_membership: Membership, actor: Membership, embedding: List[float]) -> FaceEnrollment:
        """
        Executes an HR-driven enrollment operation. 
        Bypasses queues to immediately activate the biometric profile and soft-deactivates any old active signatures.
        """
        FaceEnrollmentValidator.validate_embedding_structure(embedding)
        
        # Deactivate previous active profiles to preserve uniqueness constraints
        cls.revoke_membership_enrollments(
            membership=target_membership, 
            actor=actor, 
            reason="Profile superseded by new HR administrator registration assignment transaction."
        )

        enrollment = FaceEnrollment.objects.create(
            company=company,
            membership=target_membership,
            enrollment_source=EnrollmentSourceChoices.HR,
            embedding=embedding,
            status=EnrollmentStatusChoices.APPROVED,
            liveness_verified=True,
            approved_by=actor,
            approved_at=timezone.now()
        )
        return enrollment

    @classmethod
    @transaction.atomic
    def approve_enrollment(cls, *, enrollment: FaceEnrollment, actor: Optional[Membership]) -> FaceEnrollment:
        """
        Approves a pending registration profile.
        Activates the target signature and soft-deactivates any previously active face mappings.
        """
        FaceEnrollmentValidator.validate_status_transition(enrollment.status, EnrollmentStatusChoices.APPROVED)
        
        # Soft-deactivate previous profiles to maintain data integrity tracking bounds
        cls.revoke_membership_enrollments(
            membership=enrollment.membership,
            actor=actor,
            reason="Profile superseded by new biometric template activation approval."
        )

        enrollment.status = EnrollmentStatusChoices.APPROVED
        enrollment.approved_by = actor
        enrollment.approved_at = timezone.now()
        enrollment.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        return enrollment

    @classmethod
    @transaction.atomic
    def reject_enrollment(cls, *, enrollment: FaceEnrollment, actor: Membership, reason: str) -> FaceEnrollment:
        """
        Rejects a pending employee enrollment submission request.
        """
        if not reason.strip():
            raise DjangoValidationError(_("An explicit narrative explanation reason must be logged for administrative rejections."))

        FaceEnrollmentValidator.validate_status_transition(enrollment.status, EnrollmentStatusChoices.REJECTED)

        enrollment.status = EnrollmentStatusChoices.REJECTED
        enrollment.rejection_reason = reason
        # Overuse approver slots for tracking accountability loops
        enrollment.approved_by = actor
        enrollment.save(update_fields=["status", "rejection_reason", "approved_by", "updated_at"])
        return enrollment

    @classmethod
    @transaction.atomic
    def revoke_enrollment(cls, *, enrollment: FaceEnrollment, actor: Optional[Membership], reason: str) -> FaceEnrollment:
        """
        Manually revokes an active approved biometric template configuration.
        """
        FaceEnrollmentValidator.validate_status_transition(enrollment.status, EnrollmentStatusChoices.REVOKED)

        enrollment.status = EnrollmentStatusChoices.REVOKED
        enrollment.revoked_by = actor
        enrollment.revoked_at = timezone.now()
        enrollment.revocation_reason = reason or "Explicitly deactivated via administrative configuration changes."
        enrollment.save(update_fields=["status", "revoked_by", "revoked_at", "revocation_reason", "updated_at"])
        return enrollment

    @classmethod
    @transaction.atomic
    def revoke_membership_enrollments(cls, *, membership: Membership, actor: Optional[Membership], reason: str) -> None:
        """
        Deactivates all active approved records assigned to an employee profile.
        Used primarily during re-enrollment replacements or offboarding procedures.
        """
        active_profiles = FaceEnrollment.objects.filter(
            membership=membership,
            status=EnrollmentStatusChoices.APPROVED
        )
        for profile in active_profiles:
            cls.revoke_enrollment(enrollment=profile, actor=actor, reason=reason)