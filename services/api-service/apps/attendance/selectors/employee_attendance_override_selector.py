from typing import Optional
from apps.companies.models import Company, Membership
from apps.attendance.models.employee_attendance_override import EmployeeAttendanceOverride


class EmployeeAttendanceOverrideSelector:
    """
    Optimized data access selectors for Employee Exceptions.
    """
    @classmethod
    def get_queryset(cls):
        return EmployeeAttendanceOverride.objects.select_related("company", "membership__user")

    @classmethod
    def get_active_override(cls, company: Company, membership: Membership) -> Optional[EmployeeAttendanceOverride]:
        """
        Finds an active employee exception profile using performance-optimized pre-fetches.
        """
        return cls.get_queryset().prefetch_related(
            "allowed_methods", 
            "allowed_locations"
        ).filter(company=company, membership=membership, is_active=True).first()