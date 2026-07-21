# apps/memberships/selectors/membership_selector.py

from typing import Optional
from django.db.models import QuerySet

from apps.companies.models import Membership


class MembershipSelector:
    """
    Read-only data access layer for Membership models.

    Provides tenant-scoped membership lookups for validators,
    services, and other selectors. Never mutates data.
    """

    # ------------------------------------------------------------------
    # Base QuerySet
    # ------------------------------------------------------------------

    @classmethod
    def _base_qs(cls) -> QuerySet[Membership]:
        """
        Base queryset with common select_related optimizations.
        """
        return Membership.objects.select_related(
            "user",
            "company",
            "role",
            "department",
        )

    # ------------------------------------------------------------------
    # Existence Checks
    # ------------------------------------------------------------------

    @classmethod
    def exists(
        cls,
        membership_id: Optional[int],
        company_id: Optional[int] = None,
    ) -> bool:
        """
        Check if a membership exists.

        If company_id is provided, also verifies the membership
        belongs to that company (multi-tenant safety).

        Args:
            membership_id: The membership primary key.
            company_id: Optional company ID to scope the check.

        Returns:
            True if the membership exists (and belongs to company if specified).
        """
        if membership_id is None:
            return False

        qs = Membership.objects.filter(id=membership_id)

        if company_id is not None:
            qs = qs.filter(company_id=company_id)

        return qs.exists()

    # ------------------------------------------------------------------
    # Single Object Fetch
    # ------------------------------------------------------------------

    @classmethod
    def get_by_id(
        cls,
        membership_id: int,
        company_id: Optional[int] = None,
    ) -> Optional[Membership]:
        """
        Fetch a single membership by ID.

        Args:
            membership_id: The membership primary key.
            company_id: Optional company ID to scope the check.

        Returns:
            Membership instance or None if not found.
        """
        qs = cls._base_qs().filter(id=membership_id)

        if company_id is not None:
            qs = qs.filter(company_id=company_id)

        return qs.first()

    @classmethod
    def get_by_user(
        cls,
        user_id: int,
        company_id: int,
    ) -> Optional[Membership]:
        """
        Fetch a membership for a specific user within a company.

        Args:
            user_id: The user primary key.
            company_id: The company primary key.

        Returns:
            Membership instance or None if not found.
        """
        return (
            cls._base_qs()
            .filter(user_id=user_id, company_id=company_id)
            .first()
        )

    # ------------------------------------------------------------------
    # Company-Scoped Lists
    # ------------------------------------------------------------------

    @classmethod
    def get_company_members(
        cls,
        company_id: int,
        is_active: Optional[bool] = None,
        department_id: Optional[int] = None,
    ) -> QuerySet[Membership]:
        """
        Return all memberships for a company.

        Args:
            company_id: The company primary key.
            is_active: Optional filter by active status.
            department_id: Optional filter by department.

        Returns:
            QuerySet of Membership instances.
        """
        qs = cls._base_qs().filter(company_id=company_id)

        if is_active is not None:
            qs = qs.filter(is_active=is_active)

        if department_id is not None:
            qs = qs.filter(department_id=department_id)

        return qs.order_by("-joined_at")

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    @classmethod
    def count_members(
        cls,
        company_id: int,
        is_active: Optional[bool] = None,
    ) -> int:
        """
        Count memberships for a company.

        Args:
            company_id: The company primary key.
            is_active: Optional filter by active status.

        Returns:
            Number of memberships.
        """
        qs = Membership.objects.filter(company_id=company_id)

        if is_active is not None:
            qs = qs.filter(is_active=is_active)

        return qs.count()