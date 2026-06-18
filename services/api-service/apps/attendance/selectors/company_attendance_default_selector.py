from typing import Optional
from apps.companies.models import Company
from apps.attendance.models.company_attendance_default import CompanyAttendanceDefault


class CompanyAttendanceDefaultSelector:
    """
    Optimized data access selectors for Company Attendance Defaults.
    """
    @classmethod
    def get_queryset(cls):
        return CompanyAttendanceDefault.objects.select_related("company")

    @classmethod
    def get_active_default(cls, company: Company) -> Optional[CompanyAttendanceDefault]:
        """
        Returns the active company-wide default configuration using optimized pre-fetches.
        """
        return cls.get_queryset().prefetch_related(
            "allowed_methods", 
            "allowed_locations"
        ).filter(company=company, is_active=True).first()