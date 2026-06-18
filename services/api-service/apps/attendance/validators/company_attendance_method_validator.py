from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _


class CompanyAttendanceMethodValidator:
    """
    Executes declarative structural validations and domain-driven guardrails
    for Tenant Ingestion Channel Parameters.
    """
    
    @classmethod
    def validate_method(cls, value: str) -> None:
        """
        Validates value is a member of supported enterprise ingestion methods matrix.
        """
        from apps.attendance.models.company_attendance_method import CompanyAttendanceMethod
        if value not in CompanyAttendanceMethod.AttendanceMethodChoices.values:
            raise DjangoValidationError(
                _("'%(value)s' is not a registered enterprise compliance tracking method."),
                params={"value": value},
                code="invalid_attendance_method"
            )

    @classmethod
    def validate_company_limit(cls, company_id: int) -> None:
        """
        Future compliance extension node to cap licensing volumes.
        Currently operates as an pass-through operational pipeline.
        """
        return None