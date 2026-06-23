from datetime import datetime, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from apps.attendance.models.attendance_event import AttendanceEventTypes


class AttendanceEventValidator:
    """
    Enforces corporate finite tracking guardrails and timezone sanity thresholds.
    """

    @classmethod
    def validate_workflow_state_transition(cls, current_status: str, incoming_action: str) -> None:
        """
        Enforces state machine progression restrictions before persisting punch events.
        Supported States: "NOT_CHECKED_IN", "PRESENT", "ON_BREAK", "CHECKED_OUT"
        """
        status_upper = str(current_status).upper()

        if incoming_action == AttendanceEventTypes.CHECK_IN:
            # ✅ FIXED: Blocks duplicate clock-ins if already on duty
            if status_upper in ["PRESENT", "ON_BREAK"]:
                raise DjangoValidationError(_("Action rejected. An active shift tracking block is already running."))
                
        elif incoming_action == AttendanceEventTypes.CHECK_OUT:
            # ✅ FIXED: Accounted for NOT_CHECKED_IN status state base lines safely
            if status_upper in ["NOT_CHECKED_IN", "ABSENT"]:
                raise DjangoValidationError(_("Action rejected. Cannot initiate checkout parameters without an active check-in."))
            if status_upper == "CHECKED_OUT":
                raise DjangoValidationError(_("Action rejected. Shift tracking context already terminated for today."))
            if status_upper == "ON_BREAK":
                raise DjangoValidationError(_("Action rejected. Terminate open break intermissions before recording a check-out."))
                
        elif incoming_action == AttendanceEventTypes.BREAK_OUT:
            # ✅ FIXED: Enforces that break-outs require a true active PRESENT state match
            if status_upper != "PRESENT":
                raise DjangoValidationError(_("Action rejected. Break intermissions require a running 'PRESENT' shift context."))
                
        elif incoming_action == AttendanceEventTypes.BREAK_IN:
            if status_upper != "ON_BREAK":
                raise DjangoValidationError(_("Action rejected. Cannot process break return execution outside of active 'ON_BREAK' cycles."))

    @classmethod
    def validate_event_time_sanity(cls, event_time: datetime) -> None:
        """ Blocks impossible future timestamps. """
        future_buffer = timezone.now() + timedelta(minutes=5)
        if event_time > future_buffer:
            raise DjangoValidationError(_("Timestamps cannot be mapped into impossible future metrics windows."))