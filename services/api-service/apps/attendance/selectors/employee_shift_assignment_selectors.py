import datetime
from typing import Any, Optional
from django.db.models import QuerySet, Q
from django.utils import timezone
from apps.attendance.models import EmployeeShiftAssignment


class EmployeeShiftAssignmentSelector:
    """
    Selector class handling all read-only query logic and date-effective evaluations
    for employee shift assignments. Acts as the core data engine for attendance calculations.
    """

    # =====================================================
    # BASE QUERYSET
    # =====================================================

    @staticmethod
    def get_queryset() -> QuerySet[EmployeeShiftAssignment]:
        """
        Returns the optimized base queryset for shift assignments.
        
        PERFORMANCE OPTIMIZATION:
        - Uses select_related to eagerly pull core relational entities via SQL joins,
          preventing N+1 query loops when processing high-volume calculations.
        """
        return EmployeeShiftAssignment.objects.select_related(
            "membership",
            "membership__user",
            "shift",
            "assigned_by",
            "assigned_by__user"
        ).order_by("-effective_from")

    # =====================================================
    # SINGLE OBJECT LOOKUPS
    # =====================================================

    @staticmethod
    def get_by_id(*, assignment_id: Any, company: Any) -> Optional[EmployeeShiftAssignment]:
        """
        Retrieves a single shift assignment by its primary key database ID.
        Strictly enforces tenant company visibility boundaries.
        """
        try:
            return EmployeeShiftAssignmentSelector.get_queryset().get(
                id=assignment_id,
                membership__company=company
            )
        except EmployeeShiftAssignment.DoesNotExist:
            return None

    @staticmethod
    def get_by_public_id(*, public_id: Any, company: Any) -> Optional[EmployeeShiftAssignment]:
        """
        Retrieves an assignment by its public identifier. Falls back to the primary key
        lookup to match the structural properties of the current database schema.
        """
        try:
            return EmployeeShiftAssignmentSelector.get_queryset().get(
                id=public_id,
                membership__company=company
            )
        except (EmployeeShiftAssignment.DoesNotExist, ValueError):
            return None

    # =====================================================
    # LIST & HISTORICAL QUERIES
    # =====================================================

    @staticmethod
    def list_company_assignments(
        *,
        company: Any,
        membership_id: Optional[Any] = None,
        shift_id: Optional[Any] = None,
        active_only: bool = False,
        ordering: str = "-effective_from"
    ) -> QuerySet[EmployeeShiftAssignment]:
        """
        Compiles a filtered collection of shift assignments for a company tenant.
        Supports filtering by specific employees, schedules, or open active dates.
        """
        queryset = EmployeeShiftAssignmentSelector.get_queryset().filter(
            membership__company=company
        )

        if membership_id:
            queryset = queryset.filter(membership_id=membership_id)

        if shift_id:
            queryset = queryset.filter(shift_id=shift_id)

        if active_only:
            today = timezone.localdate()
            queryset = queryset.filter(
                is_active=True,
                effective_from__lte=today
            ).filter(
                Q(effective_until__isnull=True) | Q(effective_until__gte=today)
            )

        return queryset.order_by(ordering)

    @staticmethod
    def get_assignment_history(*, membership: Any) -> QuerySet[EmployeeShiftAssignment]:
        """
        Returns all historical and planned shift assignments for a specific employee,
        sorted chronologically descending.
        """
        return EmployeeShiftAssignmentSelector.get_queryset().filter(
            membership=membership
        )

    # =====================================================
    # ATTENDANCE RESOLUTION SUPPORT
    # =====================================================

    @staticmethod
    def get_current_assignment(
        *,
        membership: Any,
        target_date: Optional[datetime.date] = None
    ) -> Optional[EmployeeShiftAssignment]:
        """
        Resolves the exact shift assignment that was active for an employee on a specific date.
        Falls back to the current local date if no target date is supplied.
        """
        if target_date is None:
            target_date = timezone.localdate()

        # Filter assignments where: effective_from <= target_date AND (effective_until IS NULL OR effective_until >= target_date)
        queryset = EmployeeShiftAssignmentSelector.get_queryset().filter(
            membership=membership,
            is_active=True,
            effective_from__lte=target_date
        ).filter(
            Q(effective_until__isnull=True) | Q(effective_until__gte=target_date)
        )

        # Returns the newest matching assignment based on ordering properties
        return queryset.first()

    @staticmethod
    def get_active_assignments(*, company: Any) -> QuerySet[EmployeeShiftAssignment]:
        """
        Returns a snapshot of all actively running shift assignments across the entire company today.
        Used primarily by operational real-time tracking dashboards.
        """
        today = timezone.localdate()
        return EmployeeShiftAssignmentSelector.get_queryset().filter(
            membership__company=company,
            is_active=True,
            effective_from__lte=today
        ).filter(
            Q(effective_until__isnull=True) | Q(effective_until__gte=today)
        )

    # =====================================================
    # VALIDATION HELPERS
    # =====================================================

    @staticmethod
    def has_overlapping_assignment(
        *,
        membership: Any,
        effective_from: datetime.date,
        effective_until: Optional[datetime.date] = None,
        exclude_id: Optional[Any] = None
    ) -> bool:
        """
        Checks for any schedule conflicts where an existing timeline overlaps with a proposed range.
        Handles open-ended assignments (where effective_to is NULL) safely in memory and database execution.
        """
        # Base filter tracking active rows for this specific individual contributor
        queryset = EmployeeShiftAssignment.objects.filter(
            membership=membership,
            is_active=True
        )

        if exclude_id is not None:
            queryset = queryset.exclude(id=exclude_id)

        # 1. Evaluate conflicts against open-ended prospective allocations (new effective_to is NULL)
        if effective_until is None:
            # Overlaps any record whose effective_until is greater than the new effective_from, OR is also open-ended
            overlap_condition = Q(effective_until__isnull=True) | Q(effective_until__gte=effective_from)
            return queryset.filter(overlap_condition).exists()

        # 2. Evaluate conflicts against bounded prospective allocations (new effective_to is explicitly set)
        # Condition formula: existing.effective_from <= new.effective_to AND (existing.effective_until >= new.effective_from OR existing.effective_until IS NULL)
        overlap_condition = Q(effective_from__lte=effective_until) & (
            Q(effective_until__gte=effective_from) | Q(effective_until__isnull=True)
        )

        return queryset.filter(overlap_condition).exists()