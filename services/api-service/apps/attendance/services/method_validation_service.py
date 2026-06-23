import math
from typing import Any, Dict, List
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from apps.companies.models import Company, Membership
from apps.attendance.models.attendance_event import AttendanceMethodChoices
from apps.attendance.models.biometric_log import ProcessingStatusChoices
from apps.attendance.selectors.attendance_access_rule_selector import AttendanceAccessRuleSelector
from apps.attendance.selectors.company_attendance_default_selector import CompanyAttendanceDefaultSelector
from apps.attendance.selectors.employee_attendance_override_selector import EmployeeAttendanceOverrideSelector
from apps.attendance.services.method_verification_token_service import MethodVerificationTokenService


class MethodValidationService:
    """
    Validates punch evidence against organizational guardrails.
    Uses secure verification tokens instead of trusting frontend booleans.
    """
    
    # =====================================================
    # METHOD RESOLUTION
    # =====================================================
    
    @classmethod
    def resolve_allowed_methods_matrix(cls, *, company: Company, membership: Membership) -> dict:
        override = EmployeeAttendanceOverrideSelector.get_active_override(
            company=company, membership=membership
        )
        if override:
            return {
                "methods": list(override.allowed_methods.values_list("method", flat=True)),
                "locations": list(override.allowed_locations.all()),
                "validation_mode": getattr(override, "validation_mode", "ANY"),
            }
        
        rule = AttendanceAccessRuleSelector.get_highest_priority_rule(
            company=company, membership=membership
        )
        if rule:
            return {
                "methods": list(rule.allowed_methods.values_list("method", flat=True)),
                "locations": list(rule.allowed_locations.all()),
                "validation_mode": getattr(rule, "validation_mode", "ANY"),
            }
        
        default_config = CompanyAttendanceDefaultSelector.get_active_default(company=company)
        if default_config:
            return {
                "methods": list(default_config.allowed_methods.values_list("method", flat=True)),
                "locations": list(default_config.allowed_locations.all()),
                "validation_mode": getattr(default_config, "validation_mode", "ANY"),
            }
        
        raise DjangoValidationError(
            _("No attendance access configuration found for this employee.")
        )
    
    # =====================================================
    # GPS VALIDATION
    # =====================================================
    
    @classmethod
    def _calculate_haversine_distance(
        cls, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        R = 6371000.0  # Radius of the earth in meters
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = (
            math.sin(delta_phi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return R * c
    
    @classmethod
    def validate_gps_and_create_token(
        cls,
        *,
        company: Company,
        membership: Membership,
        latitude: float,
        longitude: float,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        matrix = cls.resolve_allowed_methods_matrix(company=company, membership=membership)
        locations = matrix["locations"]
        
        if not locations:
            raise DjangoValidationError(
                _("No locations configured for GPS attendance.")
            )
        
        matched_perimeter = None
        shortest_distance = float("inf")
        
        for loc in locations:
            distance = cls._calculate_haversine_distance(
                float(latitude), float(longitude),
                float(loc.latitude), float(loc.longitude)
            )
            if distance <= loc.radius_meters and distance < shortest_distance:
                matched_perimeter = loc
                shortest_distance = distance
        
        if not matched_perimeter:
            raise DjangoValidationError(
                _("Your location falls outside your assigned office geofence perimeters.")
            )
        
        token = MethodVerificationTokenService.create_gps_token(
            company=company,
            membership=membership,
            location=matched_perimeter,
            distance_meters=shortest_distance,
            latitude=latitude,
            longitude=longitude,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return {
            "verified": True,
            "token": str(token.id),
            "location_name": matched_perimeter.name,
            "distance_meters": round(shortest_distance, 2),
            "expires_in_seconds": 300,
        }
    
    # =====================================================
    # FACE VALIDATION WITH SCIPY MATH
    # =====================================================
    
    @classmethod
    def validate_face_and_create_token(
        cls,
        *,
        company: Company,
        membership: Membership,
        image_base64: str = None,
        face_embedding: List[float] = None,
        verification_method: str = "browser_embedding",
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        # 1. Look up strictly approved face profile records only
        active_face = membership.face_enrollments.filter(status="APPROVED").first()
        if not active_face:
            raise DjangoValidationError(
                _("No active, approved face enrollment profile found. Access denied.")
            )
        
        if verification_method == "browser_embedding":
            if not face_embedding:
                raise DjangoValidationError(_("Biometric vector payload parameters are empty."))
            
            stored_embedding = getattr(active_face, "embedding", None)
            if not stored_embedding:
                raise DjangoValidationError(
                    _("Enrolled profile structural matrix is corrupted. Re-enrollment required.")
                )
            
            # 2. Compute true production cosine distance using scipy backend layers
            from scipy.spatial.distance import cosine as scipy_cosine
            try:
                # Cosine distance = 1 - Cosine Similarity
                cosine_distance = scipy_cosine(face_embedding, stored_embedding)
                confidence = float(1.0 - cosine_distance)
            except Exception:
                raise DjangoValidationError(_("Biometric array structural processing error."))
            
            threshold = getattr(active_face, "similarity_threshold", 0.93)
            
            # 3. Security Anti-Spoofing Gate Check
            if confidence < threshold:
                raise DjangoValidationError(
                    _("Facial identity vector structure mismatch. Access denied.")
                )
        
        elif verification_method == "backend_ai" and image_base64:
            raise DjangoValidationError(_("Backend inference engines are disabled."))
        else:
            raise DjangoValidationError(_("Malformed verification matrix parameters."))
        
        token = MethodVerificationTokenService.create_face_token(
            company=company,
            membership=membership,
            face_enrollment=active_face,
            confidence=confidence,
            verification_method=verification_method,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        return {
            "verified": True,
            "token": str(token.id),
            "confidence": round(confidence, 4),
            "expires_in_seconds": 300,
        }
    
    # =====================================================
    # MAIN PIPELINE
    # =====================================================
    
    @classmethod
    def validate_pipeline_evidence(
        cls,
        *,
        company: Company,
        membership: Membership,
        method: str,
        evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        matrix = cls.resolve_allowed_methods_matrix(company=company, membership=membership)
        normalize_method = str(method).upper()
        allowed_methods_upper = [str(m).upper() for m in matrix["methods"]]
        
        requested_sub_methods = normalize_method.split('_')
        
        if normalize_method != "MANUAL":
            for sub_method in requested_sub_methods:
                if sub_method not in allowed_methods_upper:
                    raise DjangoValidationError(
                        _("This attendance method is not allowed for your profile.")
                    )
        
        if normalize_method == "MANUAL":
            return {
                "location": None,
                "face_enrollment": None,
                "biometric_log": None,
                "payload": {"method": "MANUAL", "reason": evidence.get("reason", "")},
            }
        
        biometric_log = None
        if normalize_method == "BIOMETRIC":
            log_id = evidence.get("biometric_log_id")
            if not log_id:
                raise DjangoValidationError(
                    _("Biometric log ID is required for biometric attendance.")
                )
            
            from apps.attendance.models.biometric_log import BiometricLog
            blog = BiometricLog.objects.filter(id=log_id, company=company).first()
            if not blog or blog.membership_id != membership.id:
                raise DjangoValidationError(
                    _("Invalid biometric log for this employee.")
                )
            biometric_log = blog
        
        token_context = MethodVerificationTokenService.validate_tokens_for_punch(
            company=company,
            membership=membership,
            method=method,
            evidence=evidence,
        )
        
        payload = token_context["verification_payload"]
        if biometric_log:
            payload["biometric"] = {
                "log_id": biometric_log.id,
                "device_user_id": biometric_log.device_user_id,
            }
        
        return {
            "location": token_context["location"],
            "face_enrollment": token_context["face_enrollment"],
            "biometric_log": biometric_log,
            "payload": payload,
        }