import datetime
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _


class BiometricLogValidator:
    """
    Enforces format constraints and multi-tenant boundary checks on raw biometric signals.
    """

    @classmethod
    def validate_log_payload_parameters(cls, data: dict) -> None:
        """
        Validates core input fields for device logging data payloads.
        """
        device_user_id = data.get("device_user_id")
        punch_time = data.get("punch_time")

        if not device_user_id or not str(device_user_id).strip():
            raise DjangoValidationError(_("Biometric user reference tracking string tags cannot look blank."))

        if punch_time:
            future_limit = timezone.now() + datetime.timedelta(days=1)
            if punch_time > future_limit:
                raise DjangoValidationError(_("Punches cannot be registered in the future."))

    @classmethod
    def validate_entity_tenant_alignment(cls, company, device=None, membership=None) -> None:
        """
        Enforces tenant isolation by verifying that referenced companies, devices, and memberships align.
        """
        if device and device.company_id != company.id:
            raise DjangoValidationError(_("The selected biometric terminal does not belong to this company context."))

        if membership and membership.company_id != company.id:
            raise DjangoValidationError(_("The resolved employee identity map context target profile does not belong to this company context."))