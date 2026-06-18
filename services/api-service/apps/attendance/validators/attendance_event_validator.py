import datetime
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from apps.attendance.models.attendance_event import AttendanceEventTypes


class AttendanceEventValidator:
    """
    Enforces workflow status transitions and timezone sanity thresholds.
    """

    @classmethod
    def validate_workflow_state_transition(cls, current_status: str, incoming_action: str) -> None:
        """
        Enforces corporate finite tracking guardrails before persisting events.
        """
        if incoming_action == AttendanceEventTypes.CHECK_IN:
            if current_status in ["PRESENT", "ON_BREAK"]:
                raise DjangoValidationError(_("Action rejected. An active shift tracking block is already running."))
                
        elif incoming_action == AttendanceEventTypes.CHECK_OUT:
            if current_status == "ABSENT":
                raise DjangoValidationError(_("Action rejected. Cannot initiate checkout parameters without an active check-in."))
            if current_status == "CHECKED_OUT":
                raise DjangoValidationError(_("Action rejected. Shift tracking context already terminated for today."))
            if current_status == "ON_BREAK":
                raise DjangoValidationError(_("Action rejected. Terminate open break intermissions before recording a check-out."))
                
        elif incoming_action == AttendanceEventTypes.BREAK_OUT:
            if current_status != "PRESENT":
                raise DjangoValidationError(_("Action rejected. Break intermissions require a running 'PRESENT' shift context."))
                
        elif incoming_action == AttendanceEventTypes.BREAK_IN:
            if current_status != "ON_BREAK":
                raise DjangoValidationError(_("Action rejected. Cannot process break return execution outside of active 'ON_BREAK' cycles."))

    @classmethod
    def validate_event_time_sanity(cls, event_time: datetime.datetime) -> None:
        """ Blocks impossible future timestamps. """
        future_buffer = timezone.now() + datetime.timedelta(minutes=5)
        if event_time > future_buffer:
            raise DjangoValidationError(_("Timestamps cannot be mapped into impossible future metrics windows."))