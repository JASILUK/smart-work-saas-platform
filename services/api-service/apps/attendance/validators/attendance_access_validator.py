from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.attendance.models.company_attendance_default import CompanyAttendanceDefault
from apps.attendance.models.attendance_access_rule import AttendanceAccessRule, ScopeTypeChoices
from apps.attendance.models.employee_attendance_override import EmployeeAttendanceOverride


class AttendanceAccessValidator:
    """
    Validates business logic constraints across the entire access matrix layer.
    """

    @classmethod
    def validate_method_and_locations(cls, method_ids: list, location_ids: list, company) -> None:
        """
        Validates cross-dependencies between active access channels and geofences.
        """
        from apps.attendance.models.company_attendance_method import CompanyAttendanceMethod
        
        # Verify that all provided methods are active in this company scope
        methods = CompanyAttendanceMethod.objects.filter(id__in=method_ids, company=company, is_active=True)
        if len(methods) != len(method_ids):
            raise ValidationError(_("One or more selected attendance methods are inactive or invalid."))

        if not method_ids:
            raise ValidationError(_("At least one allowed attendance method must be selected."))

        # Enforce geofencing structural rules if GPS tracking is selected
        has_gps = any(m.method == "GPS" for m in methods)
        if has_gps and not location_ids:
            raise ValidationError(_("GPS attendance tracking requires assigning at least one allowed location."))

    @classmethod
    def validate_default_uniqueness(cls, company, exclude_id: int = None) -> None:
        """
        Ensures that only one default parameter set remains active for a company context.
        """
        queryset = CompanyAttendanceDefault.objects.filter(company=company, is_active=True)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        if queryset.exists():
            raise ValidationError(_("An active default attendance configuration already exists for this company."))

    @classmethod
    def validate_rule_constraints(cls, rule: AttendanceAccessRule, method_ids: list, location_ids: list) -> None:
        """
        Validates access rule priorities, scope parameters, and structural combinations.
        """
        if rule.priority < 1:
            raise ValidationError(_("Evaluation priority index value must be greater than or equal to 1."))

        if rule.scope_type == ScopeTypeChoices.WORK_MODE and not rule.work_mode:
            raise ValidationError(_("A valid work mode must be designated for rules targeting work mode scope type."))
            
        if rule.scope_type == ScopeTypeChoices.DEPARTMENT and not rule.department:
            raise ValidationError(_("A target organizational department must be assigned for rules targeting department scope type."))

        # Verify that combinations remain unique across the active database scope
        queryset = AttendanceAccessRule.objects.filter(
            company=rule.company,
            scope_type=rule.scope_type,
            work_mode=rule.work_mode,
            department=rule.department,
            is_active=True
        ).exclude(id=rule.id)
        
        if queryset.exists():
            raise ValidationError(_("An active configuration override rule already exists for this scope pattern combination."))

    @classmethod
    def validate_override_uniqueness(cls, membership, exclude_id: int = None) -> None:
        """
        Ensures an individual worker can only be assigned a single active override exception at a time.
        """
        queryset = EmployeeAttendanceOverride.objects.filter(membership=membership, is_active=True)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        if queryset.exists():
            raise ValidationError(_("This employee already has an active attendance exception profile."))