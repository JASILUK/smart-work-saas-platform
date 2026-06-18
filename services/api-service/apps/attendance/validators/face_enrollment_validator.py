from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from apps.attendance.models.company_face_policy import CompanyFaceEnrollmentPolicy, PolicyTypeChoices
from apps.attendance.models.face_enrollment import FaceEnrollment, EnrollmentStatusChoices


class FaceEnrollmentValidator:
    """
    Validates vector data arrays, multi-tenant compliance guidelines, 
    and transaction state sequences for face enrollment processes.
    """

    @classmethod
    def validate_embedding_structure(cls, embedding: any) -> None:
        """
        Validates the math vector array consists entirely of structured floating-point coordinates.
        """
        if not isinstance(embedding, list):
            raise DjangoValidationError(_("Biometric vector data payload must be passed as an array list structure."))
        if not embedding:
            raise DjangoValidationError(_("Biometric array coordinates package cannot look empty."))
        
        # Cross-reference value fields constraints parameters
        if not all(isinstance(x, (int, float)) for x in embedding):
            raise DjangoValidationError(_("Vector coordinate dimensions array must consist entirely of continuous numeric floats."))
            
        # Standard validation node ensuring compatibility with standard face model feature lengths
        if len(embedding) not in [128, 512, 1024]:
            raise DjangoValidationError(_("Vector feature list dimension size (%(length)d) fails model architecture constraints."), params={"length": len(embedding)})

    @classmethod
    def validate_policy_compliance(cls, policy: CompanyFaceEnrollmentPolicy, source: str) -> None:
        """
        Enforces policy restrictions based on enrollment source (Employee vs HR).
        """
        if policy.policy_type == PolicyTypeChoices.HR_ONLY and source == "EMPLOYEE":
            raise DjangoValidationError(_("Tenant operational parameters restrict profile registrations entirely to HR administrators."))

    @classmethod
    def validate_status_transition(cls, current_status: str, target_status: str) -> None:
        """
        Enforces the finite state machine transitions for enrollments:
        PENDING -> APPROVED or REJECTED
        APPROVED -> REVOKED
        """
        allowed_paths = {
            EnrollmentStatusChoices.PENDING: [EnrollmentStatusChoices.APPROVED, EnrollmentStatusChoices.REJECTED],
            EnrollmentStatusChoices.APPROVED: [EnrollmentStatusChoices.REVOKED],
            EnrollmentStatusChoices.REJECTED: [],
            EnrollmentStatusChoices.REVOKED: []
        }

        if target_status not in allowed_paths.get(current_status, []):
            raise DjangoValidationError(
                _("Invalid operational lifecycle transaction. Cannot transition profile configuration state from '%(curr)s' directly to '%(target)s'."),
                params={"curr": current_status, "target": target_status}
            )

    @classmethod
    def validate_uniqueness(cls, company, membership, exclude_id: int = None) -> None:
        """
        Ensures that an individual employee can have only one APPROVED face model registration row at a time.
        """
        queryset = FaceEnrollment.objects.filter(
            company=company,
            membership=membership,
            status=EnrollmentStatusChoices.APPROVED
        )
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
            
        if queryset.exists():
            raise DjangoValidationError(_("This employee already possesses an active approved biometrics face enrollment map profile."))