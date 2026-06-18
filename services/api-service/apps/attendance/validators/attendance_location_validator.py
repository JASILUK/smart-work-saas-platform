from decimal import Decimal
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from apps.companies.models import Company
from apps.attendance.selectors.company_attendance_method_selector import CompanyAttendanceMethodSelector


class AttendanceLocationValidator:
    """
    Executes structural coordinate range assessments and multi-tenant domain alignment rules
    for localized geofence parameters.
    """

    @classmethod
    def validate_latitude(cls, value: Decimal) -> None:
        """ Ensures latitude falls within standard global bounds [-90, 90]. """
        if value < Decimal("-90.000000") or value > Decimal("90.000000"):
            raise DjangoValidationError(
                _("Latitude value must fall explicitly within coordinate metrics range of -90.0 to 90.0.")
            )

    @classmethod
    def validate_longitude(cls, value: Decimal) -> None:
        """ Ensures longitude falls within standard global bounds [-180, 180]. """
        if value < Decimal("-180.000000") or value > Decimal("180.000000"):
            raise DjangoValidationError(
                _("Longitude value must fall explicitly within coordinate metrics range of -180.0 to 180.0.")
            )

    @classmethod
    def validate_radius(cls, value: int) -> None:
        """ Restricts radius variance size to operational bounds [20m, 1000m]. """
        if value < 20 or value > 1000:
            raise DjangoValidationError(
                _("Radius must be between 20 and 1000 meters.")
            )

    @classmethod
    def validate_gps_enabled(cls, company: Company) -> None:
        """
        Business Rule Guardrail: Blocks parameters activation if the tenant context 
        omits 'GPS' from its active structural methods configuration list.
        """
        if not CompanyAttendanceMethodSelector.is_method_enabled(company=company, method="GPS"):
            raise DjangoValidationError(
                _("GPS attendance method is not enabled for this company.")
            )