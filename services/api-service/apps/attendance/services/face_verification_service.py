import math
from typing import List
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from apps.companies.models import Company, Membership
from apps.attendance.selectors.face_enrollment_selector import FaceEnrollmentSelector



class FaceVerificationService:
    """
    Executes high-performance vector alignment verification matching operations.
    Uses pure mathematical calculations to determine compliance scores without external framework bindings.
    """

    @classmethod
    def compare_embeddings(cls, stored_embedding: List[float], live_embedding: List[float]) -> float:
        """
        Calculates the Cosine Similarity score between two floating-point vectors.
        Returns a scalar metric bounded inside [-1.0, 1.0].
        
        Formula applied:
        $$\\text{Similarity} = \\frac{A \\cdot B}{\\|A\\| \\|B\\|}$$
        """
        if len(stored_embedding) != len(live_embedding):
            raise DjangoValidationError(_("Vector coordinate payloads dimension sizes mismatch. Cannot execute cross-comparison operations."))

        dot_product = 0.0
        norm_a = 0.0
        norm_b = 0.0
        
        for a, b in zip(stored_embedding, live_embedding):
            dot_product += a * b
            norm_a += a * a
            norm_b += b * b

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return dot_product / (math.sqrt(norm_a) * math.sqrt(norm_b))

    @classmethod
    def verify_face(cls, *, company: Company, membership: Membership, live_embedding: List[float]) -> dict:
        """
        Validates an incoming clock-in face signature payload against the active database reference registration.
        Returns validation tracking summaries used by downstream check-in logs handlers.
        """
        active_enrollment = FaceEnrollmentSelector.get_active_enrollment(company=company, membership=membership)
        
        if not active_enrollment:
            raise DjangoValidationError(_("Biometric profile parameters look incomplete. No active approved face enrollment records found for this employee."))

        similarity_score = cls.compare_embeddings(
            stored_embedding=active_enrollment.embedding, 
            live_embedding=live_embedding
        )
        
        threshold = active_enrollment.similarity_threshold
        is_verified = similarity_score >= threshold

        return {
            "verified": is_verified,
            "similarity": round(similarity_score, 4),
            "threshold": threshold,
            "enrollment_id": active_enrollment.id
        }