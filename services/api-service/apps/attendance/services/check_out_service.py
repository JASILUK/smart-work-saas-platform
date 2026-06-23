from django.db import transaction
from apps.companies.models import Company, Membership
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceEventTypes
from apps.attendance.validators.attendance_event_validator import AttendanceEventValidator
from apps.attendance.validators.shift_time_validator import ShiftTimeValidator  # NEW
from apps.attendance.services.method_validation_service import MethodValidationService
from apps.attendance.services.live_attendance_service import LiveAttendanceService


class CheckOutService:
    @classmethod
    @transaction.atomic
    def check_out(
        cls,
        *,
        company: Company,
        membership: Membership,
        method: str,
        evidence: dict,
        actor: Membership
    ) -> AttendanceEvent:
        
        current_status = LiveAttendanceService.get_member_status(
            company=company, membership=membership
        )
        AttendanceEventValidator.validate_workflow_state_transition(
            current_status, AttendanceEventTypes.CHECK_OUT
        )
        
        # NEW: Simple shift time check — can't check out before shift starts
        ShiftTimeValidator.validate_check_out(company=company, membership=membership)
        
        context = MethodValidationService.validate_pipeline_evidence(
            company=company,
            membership=membership,
            method=method,
            evidence=evidence
        )
        
        log_event = AttendanceEvent.objects.create(
            company=company,
            membership=membership,
            event_type=AttendanceEventTypes.CHECK_OUT,
            attendance_method=method,
            location=context["location"],
            face_enrollment=context["face_enrollment"],
            biometric_log=context["biometric_log"],
            verification_payload=context["payload"],
            created_by=actor
        )
        
        if context["biometric_log"]:
            from apps.attendance.services.biometric_log_service import BiometricLogService
            BiometricLogService.mark_processed(log=context["biometric_log"])
        
        return log_event