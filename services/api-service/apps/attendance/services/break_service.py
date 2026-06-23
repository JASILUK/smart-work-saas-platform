from django.db import transaction
from apps.companies.models import Company, Membership
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceEventTypes
from apps.attendance.validators.attendance_event_validator import AttendanceEventValidator
from apps.attendance.services.method_validation_service import MethodValidationService
from apps.attendance.services.live_attendance_service import LiveAttendanceService


class BreakService:
    """
    Coordinates state transitions and evidence validation for starting 
    and ending employee break intermissions.
    """

    @classmethod
    @transaction.atomic
    def break_out(
        cls,
        *,
        company: Company,
        membership: Membership,
        method: str,
        evidence: dict,
        actor: Membership
    ) -> AttendanceEvent:
        """
        Begins a break intermission.
        Validates that the employee's current state evaluates to 'PRESENT'.
        """
        # Resolve current status string ("PRESENT")
        current_status = LiveAttendanceService.get_member_status(
            company=company, membership=membership
        )
        
        # Enforces the state transition to BREAK_OUT
        AttendanceEventValidator.validate_workflow_state_transition(
            current_status, AttendanceEventTypes.BREAK_OUT
        )
        
        # Validate biometric and geofence tokens
        context = MethodValidationService.validate_pipeline_evidence(
            company=company,
            membership=membership,
            method=method,
            evidence=evidence
        )
        
        return AttendanceEvent.objects.create(
            company=company,
            membership=membership,
            event_type=AttendanceEventTypes.BREAK_OUT,
            attendance_method=method,
            location=context["location"],
            face_enrollment=context["face_enrollment"],
            biometric_log=context["biometric_log"],
            verification_payload=context["payload"],
            created_by=actor
        )
    
    @classmethod
    @transaction.atomic
    def break_in(
        cls,
        *,
        company: Company,
        membership: Membership,
        method: str,
        evidence: dict,
        actor: Membership
    ) -> AttendanceEvent:
        """
        Ends an active break intermission and returns the user to active status.
        Validates that the employee's current state evaluates to 'ON_BREAK'.
        """
        # Resolve current status string ("ON_BREAK")
        current_status = LiveAttendanceService.get_member_status(
            company=company, membership=membership
        )
        
        # Enforces the state transition to BREAK_IN
        AttendanceEventValidator.validate_workflow_state_transition(
            current_status, AttendanceEventTypes.BREAK_IN
        )
        
        # Validate biometric and geofence tokens
        context = MethodValidationService.validate_pipeline_evidence(
            company=company,
            membership=membership,
            method=method,
            evidence=evidence
        )
        
        return AttendanceEvent.objects.create(
            company=company,
            membership=membership,
            event_type=AttendanceEventTypes.BREAK_IN,
            attendance_method=method,
            location=context["location"],
            face_enrollment=context["face_enrollment"],
            biometric_log=context["biometric_log"],
            verification_payload=context["payload"],
            created_by=actor
        )