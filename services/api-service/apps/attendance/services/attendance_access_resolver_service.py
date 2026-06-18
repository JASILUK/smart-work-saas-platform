from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.companies.models import Company, Membership
from apps.attendance.selectors.company_attendance_default_selector import CompanyAttendanceDefaultSelector
from apps.attendance.selectors.attendance_access_rule_selector import AttendanceAccessRuleSelector
from apps.attendance.selectors.employee_attendance_override_selector import EmployeeAttendanceOverrideSelector


class AttendanceAccessResolverService:
    """
    Core HRMS Rule Engine. Computes real-time clearance parameters 
    for an employee using strict cascade hierarchy parsing.
    """

    @classmethod
    def resolve_access(cls, *, company: Company, membership: Membership) -> dict:
        """
        Resolves attendance access following the strict resolution chain:
        Override Profile -> Dynamic Custom Rule -> Company Fallback Defaults
        """
        
        # Step 1: Check for explicit individual employee exceptions
        override = EmployeeAttendanceOverrideSelector.get_active_override(company=company, membership=membership)
        if override:
            return cls._build_resolution_payload(source="override", config_instance=override)

        # Step 2: Fall back to grouped conditional configuration rules
        rule = AttendanceAccessRuleSelector.get_highest_priority_rule(company=company, membership=membership)
        if rule:
            return cls._build_resolution_payload(source="rule", config_instance=rule)

        # Step 3: Fall back to default company parameters
        default_config = CompanyAttendanceDefaultSelector.get_active_default(company=company)
        if default_config:
            return cls._build_resolution_payload(source="default", config_instance=default_config)

        # Fail explicitly if no valid configuration fallback is found
        raise ValidationError(
            _("The system failed to compute an access profile for the designated employee context. Check organizational default setups.")
        )

    @classmethod
    def _build_resolution_payload(cls, source: str, config_instance) -> dict:
        """
        Normalizes matching entity records into standard system verification shapes.
        """
        return {
            "source": source,
            "validation_mode": config_instance.validation_mode,
            "methods": list(config_instance.allowed_methods.values_list("method", flat=True)),
            "locations": [
                {
                    "id": loc.id,
                    "name": loc.name,
                    "latitude": float(loc.latitude),
                    "longitude": float(loc.longitude),
                    "radius_meters": loc.radius_meters
                }
                for loc in config_instance.allowed_locations.all()
            ]
        }