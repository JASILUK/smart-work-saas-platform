import math
from decimal import Decimal
from typing import Any, Dict, List, Optional
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from apps.companies.models import Company, Membership
from apps.attendance.models.attendance_event import AttendanceMethodChoices
from apps.attendance.models.biometric_log import ProcessingStatusChoices
from apps.attendance.selectors.attendance_access_rule_selector import AttendanceAccessRuleSelector
from apps.attendance.selectors.company_attendance_default_selector import CompanyAttendanceDefaultSelector
from apps.attendance.selectors.employee_attendance_override_selector import EmployeeAttendanceOverrideSelector


class MethodValidationService:
    """
    Validates punch evidence against organizational geofence boundaries, 
    facial registration tokens, and multi-tenant access permission structures.
    """

    @classmethod
    def resolve_allowed_methods_matrix(cls, *, company: Company, membership: Membership) -> dict:
        """
        Resolves active tracking rules using the standard hierarchy:
        Employee Override -> Access Rule Fallback -> Company Workspace Defaults.
        """
        override = EmployeeAttendanceOverrideSelector.get_active_override(company=company, membership=membership)
        if override:
            return {"methods": list(override.allowed_methods.values_list("method", flat=True)), "locations": list(override.allowed_locations.all())}

        rule = AttendanceAccessRuleSelector.get_highest_priority_rule(company=company, membership=membership)
        if rule:
            return {"methods": list(rule.allowed_methods.values_list("method", flat=True)), "locations": list(rule.allowed_locations.all())}

        default_config = CompanyAttendanceDefaultSelector.get_active_default(company=company)
        if default_config:
            return {"methods": list(default_config.allowed_methods.values_list("method", flat=True)), "locations": list(default_config.allowed_locations.all())}

        raise DjangoValidationError(_("No structural access clearance settings configured for this workspace context scope."))

    @classmethod
    def _calculate_haversine_distance(cls, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Applies the Haversine trigonometric formula to calculate precise 
        surface distance metrics in meters between two coordinate pairs.
        """
        R = 6371000.0  # Mean radius of the Earth in meters
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return R * c

    @classmethod
    def validate_pipeline_evidence(cls, *, company: Company, membership: Membership, method: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates telemetry payloads against corporate tracking guardrails.
        """
        matrix = cls.resolve_allowed_methods_matrix(company=company, membership=membership)
        
        # Normalize checking routes
        mapped_method_verification = "GPS" if "GPS" in method else method
        if mapped_method_verification == "FACE_ONLY": mapped_method_verification = "FACE"
        
        if mapped_method_verification not in matrix["methods"] and method != "MANUAL":
            raise DjangoValidationError(_("The chosen execution channel interface is restricted for your profile context."))

        context = {"location": None, "face_enrollment": None, "biometric_log": None, "payload": {}}

        # Region: GPS Coordinate Spatial Validation
        if method in [AttendanceMethodChoices.GPS_ONLY, AttendanceMethodChoices.GPS_FACE]:
            lat = evidence.get("latitude")
            lng = evidence.get("longitude")
            if lat is None or lng is None:
                raise DjangoValidationError(_("GPS geofence evaluation requires precise latitude and longitude coordinates."))

            matched_perimeter = None
            shortest_calculated_distance = float("inf")

            for loc in matrix["locations"]:
                distance = cls._calculate_haversine_distance(float(lat), float(lng), float(loc.latitude), float(loc.longitude))
                if distance <= loc.radius_meters and distance < shortest_calculated_distance:
                    matched_perimeter = loc
                    shortest_calculated_distance = distance

            if not matched_perimeter:
                raise DjangoValidationError(_("Punch rejected. Your location falls outside your assigned geofence boundaries."))

            context["location"] = matched_perimeter
            context["payload"].update({"latitude": float(lat), "longitude": float(lng), "distance_meters": round(shortest_calculated_distance, 2)})

        # Region: Facial Verification Processing Node
        if method in [AttendanceMethodChoices.FACE_ONLY, AttendanceMethodChoices.GPS_FACE]:
            if not evidence.get("face_verified", False):
                raise DjangoValidationError(_("Facial biometric structural verification check failed at the ingestion terminal."))
            
            active_face = membership.face_enrollments.filter(status="APPROVED").first()
            if not active_face:
                raise DjangoValidationError(_("No active biometric face profile found. Complete enrollment before clocking in."))
                
            context["face_enrollment"] = active_face
            context["payload"].update({"face_verified": True, "confidence": evidence.get("confidence", 1.0)})

        # Region: Biometric Log Validation Route
        if method == AttendanceMethodChoices.BIOMETRIC:
            log_id = evidence.get("biometric_log_id")
            if not log_id:
                raise DjangoValidationError(_("Hardware transaction log ID must be linked to register biometric channel entries."))
            
            from apps.attendance.models.biometric_log import BiometricLog
            blog = BiometricLog.objects.filter(id=log_id, company=company).first()
            
            if not blog or blog.membership_id != membership.id:
                raise DjangoValidationError(_("The specified transaction log record is invalid or unassigned to this employee context."))
            if blog.processing_status == ProcessingStatusChoices.PROCESSED:
                raise DjangoValidationError(_("This transaction log event has already been consumed by an existing attendance record."))

            context["biometric_log"] = blog
            context["payload"].update({"biometric_log_id": blog.id, "device_user_id": blog.device_user_id})

        return context