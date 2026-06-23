import uuid
from datetime import timedelta
from typing import Dict, Any
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _

from apps.companies.models import Company, Membership
from apps.attendance.models.verification_token import VerificationToken


class MethodVerificationTokenService:
    """
    Creates and validates one-time verification tokens for attendance methods.
    Security layer that prevents frontend spoofing.
    """
    
    TOKEN_EXPIRY_MINUTES = 5
    
    # =====================================================
    # TOKEN CREATION
    # =====================================================
    
    @classmethod
    def create_gps_token(
        cls,
        *,
        company: Company,
        membership: Membership,
        location,
        distance_meters: float,
        latitude: float,
        longitude: float,
        ip_address: str = None,
        user_agent: str = None
    ) -> VerificationToken:
        return VerificationToken.objects.create(
            id=uuid.uuid4(),
            token_type="GPS",
            company=company,
            membership=membership,
            location=location,
            verification_payload={
                "latitude": latitude,
                "longitude": longitude,
                "distance_meters": round(distance_meters, 2),
                "location_name": location.name,
            },
            expires_at=timezone.now() + timedelta(minutes=cls.TOKEN_EXPIRY_MINUTES),
            ip_address=ip_address,
            user_agent=user_agent,
        )
    
    @classmethod
    def create_face_token(
        cls,
        *,
        company: Company,
        membership: Membership,
        face_enrollment,
        confidence: float,
        verification_method: str = "browser_embedding",
        ip_address: str = None,
        user_agent: str = None
    ) -> VerificationToken:
        return VerificationToken.objects.create(
            id=uuid.uuid4(),
            token_type="FACE",
            company=company,
            membership=membership,
            face_enrollment=face_enrollment,
            verification_payload={
                "confidence": round(confidence, 4),
                "verification_method": verification_method,
                "enrollment_id": str(face_enrollment.id),
            },
            expires_at=timezone.now() + timedelta(minutes=cls.TOKEN_EXPIRY_MINUTES),
            ip_address=ip_address,
            user_agent=user_agent,
        )
    
    # =====================================================
    # TOKEN VALIDATION
    # =====================================================
    
    @classmethod
    def validate_and_consume_token(
        cls,
        *,
        token_id: str,
        company: Company,
        membership: Membership,
        token_type: str
    ) -> Dict[str, Any]:
        # Cast tracking token safely to an explicit UUID instance to verify formatting boundaries
        try:
            target_uuid = uuid.UUID(str(token_id)) if isinstance(token_id, str) else token_id
        except (ValueError, AttributeError):
            raise DjangoValidationError(
                _({f"{token_type.lower()}_verification_token": f"Provided {token_type} identifier is not a valid UUID string format."})
            )

        try:
            token = VerificationToken.objects.select_related(
                "face_enrollment", "location"
            ).get(
                id=target_uuid,
                company=company,
                membership=membership,
                token_type=token_type
            )
        except VerificationToken.DoesNotExist:
            raise DjangoValidationError(
                _(f"{token_type} verification token is invalid or does not exist.")
            )
        
        if token.is_used:
            raise DjangoValidationError(
                _(f"{token_type} verification token has already been used. Please verify again.")
            )
        
        # Fallback check evaluating timestamp offsets cleanly
        now = timezone.now()
        if token.expires_at and token.expires_at < now:
            raise DjangoValidationError(
                _(f"{token_type} verification has expired. Please verify again.")
            )
            
        if getattr(token, 'is_expired', False) == True:
            raise DjangoValidationError(
                _(f"{token_type} verification has expired. Please verify again.")
            )
        
        if token.membership_id != membership.id:
            raise DjangoValidationError(
                _(f"{token_type} verification token does not belong to this employee.")
            )
        
        token.mark_used()
        
        return {
            "token_id": str(token.id),
            "token_type": token.token_type,
            "face_enrollment": token.face_enrollment,
            "location": token.location,
            "verification_payload": token.verification_payload,
            "verified_at": token.used_at.isoformat() if token.used_at else timezone.now().isoformat(),
        }
    
    @classmethod
    def validate_tokens_for_punch(
        cls,
        *,
        company: Company,
        membership: Membership,
        method: str,
        evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validates all required verification tokens for any punch action
        (check-in, check-out, break-out, break-in).
        """
        context = {
            "location": None,
            "face_enrollment": None,
            "verification_payload": {},
        }
        
        normalize_method = str(method).upper()
        
        # GPS validation mapping incoming raw payload choices strings cleanly
        if normalize_method in ["GPS_ONLY", "GPS_FACE"]:
            gps_token_id = evidence.get("gps_verification_token")
            if not gps_token_id:
                raise DjangoValidationError(
                    _("GPS verification token is required for this attendance method.")
                )
            
            gps_result = cls.validate_and_consume_token(
                token_id=gps_token_id,
                company=company,
                membership=membership,
                token_type="GPS"
            )
            context["location"] = gps_result["location"]
            context["verification_payload"]["gps"] = gps_result["verification_payload"]
        
        # Face validation mapping incoming raw payload choices strings cleanly
        if normalize_method in ["FACE_ONLY", "GPS_FACE"]:
            face_token_id = evidence.get("face_verification_token")
            if not face_token_id:
                raise DjangoValidationError(
                    _("Face verification token is required for this attendance method.")
                )
            
            face_result = cls.validate_and_consume_token(
                token_id=face_token_id,
                company=company,
                membership=membership,
                token_type="FACE"
            )
            context["face_enrollment"] = face_result["face_enrollment"]
            context["verification_payload"]["face"] = face_result["verification_payload"]
        
        return context