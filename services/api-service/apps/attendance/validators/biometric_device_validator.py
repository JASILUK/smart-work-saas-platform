import zoneinfo
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from apps.attendance.models.biometric_device import BiometricSyncMode


class BiometricDeviceValidator:
    """
    Enforces compliance constraints and network parameter alignment profiles for biometric terminals.
    """

    @classmethod
    def validate_device_networking(cls, data: dict) -> None:
        """
        Validates connection addresses for active pull-scheduled devices.
        """
        sync_mode = data.get("sync_mode")
        ip_address = data.get("ip_address")
        port = data.get("port")

        if sync_mode == BiometricSyncMode.PULL:
            if not ip_address:
                raise DjangoValidationError(
                    _("Devices set to PULL mode require a valid network IP address to fetch transaction records.")
                )
            if not port:
                raise DjangoValidationError(_("PULL execution targets require an active communication interface port."))

    @classmethod
    def validate_timezone_string(cls, tz_string: str) -> None:
        """
        Validates target operating timezone values match recognized structural zone naming configurations.
        """
        try:
            zoneinfo.ZoneInfo(tz_string)
        except Exception:
            raise DjangoValidationError(
                _("The provided string value '%(tz)s' is not an identified zone database entry."),
                params={"tz": tz_string}
            )

    @classmethod
    def normalize_device_code(cls, value: str) -> str:
        """
        Normalizes alphanumeric strings to uppercase.
        """
        if not value:
            raise DjangoValidationError(_("Device tracking lookup tags cannot look blank."))
        return str(value).strip().upper()