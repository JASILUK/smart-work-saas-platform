from typing import List, Optional
from django.db.models import QuerySet
from apps.companies.models import Company
from apps.attendance.models.company_attendance_method import CompanyAttendanceMethod


class CompanyAttendanceMethodSelector:
    """
    Encapsulates database lookup matrices and caching paths for Company tracking layers.
    Executes read operations via performance-optimized data layer isolation layers.
    """

    @classmethod
    def get_queryset(cls) -> QuerySet[CompanyAttendanceMethod]:
        """
        Returns basic query layer tracking optimization fields cleanly.
        """
        return CompanyAttendanceMethod.objects.select_related("company")

    @classmethod
    def get_company_methods(cls, company: Company) -> QuerySet[CompanyAttendanceMethod]:
        """
        Fetches all operational validation channels for a targeted Company tenant context.
        """
        return cls.get_queryset().filter(company=company, is_active=True)

    @classmethod
    def get_company_method(cls, company: Company, method: str) -> Optional[CompanyAttendanceMethod]:
        """
        Pulls a single contextual strategy instance regardless of execution state.
        """
        return CompanyAttendanceMethod.objects.filter(company=company, method=method).first()

    @classmethod
    def is_method_enabled(cls, company: Company, method: str) -> bool:
        """
        Evaluation matrix gatekeeper checks if a system transaction log channel 
        can process active check-in events.
        """
        return CompanyAttendanceMethod.objects.filter(
            company=company, 
            method=method, 
            is_active=True
        ).exists()