from typing import Optional

from django.db.models import QuerySet
from apps.companies.models import Company, Membership
from apps.attendance.models.attendance_access_rule import AttendanceAccessRule, ScopeTypeChoices


class AttendanceAccessRuleSelector:
    """
    Optimized data access selectors for Group Attendance Rules.
    """
    @classmethod
    def get_queryset(cls) -> QuerySet[AttendanceAccessRule]:
        return AttendanceAccessRule.objects.select_related("company", "department")

    @classmethod
    def list_company_rules(cls, company: Company) -> QuerySet[AttendanceAccessRule]:
        """
        Returns all configuration rules bound to a specific tenant company.
        """
        return cls.get_queryset().prefetch_related(
            "allowed_methods", 
            "allowed_locations"
        ).filter(company=company)

    @classmethod
    def get_matching_rules(cls, company: Company, membership: Membership) -> QuerySet[AttendanceAccessRule]:
        """
        Finds all active rules that match the employee's structural profile.
        """
        return cls.get_queryset().prefetch_related(
            "allowed_methods", 
            "allowed_locations"
        ).filter(
            company=company,
            is_active=True
        ).filter(
            (models.Q(scope_type=ScopeTypeChoices.WORK_MODE) & models.Q(work_mode=membership.work_mode)) |
            (models.Q(scope_type=ScopeTypeChoices.DEPARTMENT) & models.Q(department=membership.department))
        ).order_by("priority", "-created_at")

    @classmethod
    def get_highest_priority_rule(cls, company: Company, membership: Membership) -> Optional[AttendanceAccessRule]:
        """
        Returns the single matching rule with the highest priority (lowest numeric value).
        """
        return cls.get_matching_rules(company=company, membership=membership).first()