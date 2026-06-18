from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from apps.companies.models import Company, Membership
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceMethodChoices


class ManualAttendanceService:
    """
    Handles retro-active event adjustments initiated by HR administrators.
    """

    @classmethod
    @transaction.atomic
    def log_manual_action(cls, *, company: Company, membership: Membership, event_type: str, notes: str, actor: Membership) -> AttendanceEvent:
        if not notes or not notes.strip():
            raise DjangoValidationError(_("An explicit audit trail narrative explanation is required for manual overrides."))

        return AttendanceEvent.objects.create(
            company=company,
            membership=membership,
            event_type=event_type,
            attendance_method=AttendanceMethodChoices.MANUAL,
            notes=notes,
            created_by=actor
        )