from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _


class BiometricEmployeeMappingValidator:
    """
    Validates company alignment constraints for individual hardware mapping configurations.
    """

    @classmethod
    def validate_tenant_boundary(cls, membership, device) -> None:
        """
        Enforces tenant isolation by blocking mappings across different multi-tenant scopes.
        """
        if membership.company_id != device.company_id:
            raise DjangoValidationError(
                _("Cross-company matching is prohibited. Profile identities must share company context boundaries.")
            )

    @classmethod
    def normalize_device_user_id(cls, value: str) -> str:
        """
        Trims whitespace blocks from identity identifier tracking values.
        """
        if not value or not str(value).strip():
            raise DjangoValidationError(_("Device User ID tracker references cannot register as empty tags."))
        return str(value).strip()