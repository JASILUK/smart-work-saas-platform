from typing import Any, Optional
from django.db.models import QuerySet, Q
from apps.attendance.models import Shift


class ShiftSelector:
    """
    Selector class handling all read-only database queries and lookups for the Shift model.
    Acts as the single source of truth for shift data retrieval across the application.
    """

    # =====================================================
    # BASE QUERYSET
    # =====================================================

    @staticmethod
    def get_queryset() -> QuerySet[Shift]:
        """
        Returns the foundational base queryset for all Shift selector operations.
        Optimized with select_related("company") to eliminate N+1 overhead.
        """
        return Shift.objects.select_related("company").order_by("name")

    # =====================================================
    # SINGLE OBJECT LOOKUPS
    # =====================================================

    @staticmethod
    def get_by_id(*, shift_id: Any, company: Any) -> Optional[Shift]:
        """
        Retrieves a single shift by its database primary key identifier.
        Ensures tenant boundaries are strictly respected.
        """
        try:
            return ShiftSelector.get_queryset().get(id=shift_id, company=company)
        except Shift.DoesNotExist:
            return None

    @staticmethod
    def get_by_public_id(*, public_id: Any, company: Any) -> Optional[Shift]:
        """
        Retrieves a single shift by its public tracking identifier.
        Falls back smoothly to primary key ID lookup since an explicit public_id UUID 
        does not exist on the current model schema.
        """
        try:
            return ShiftSelector.get_queryset().get(id=public_id, company=company)
        except (Shift.DoesNotExist, ValueError):
            return None

    @staticmethod
    def get_default_shift(*, company: Any) -> Optional[Shift]:
        """
        Retrieves the company's fallback active shift context. 
        Returns the primary alpha active shift row found for the tenant.
        """
        return ShiftSelector.get_queryset().filter(
            company=company, 
            is_active=True
        ).first()

    # =====================================================
    # LIST & FILTERING QUERIES
    # =====================================================

    @staticmethod
    def list_company_shifts(
        *,
        company: Any,
        is_active: Optional[bool] = None,
        shift_type: Optional[str] = None,  # Mapped to evaluate night shift flags
        search: Optional[str] = None,
        ordering: str = "name",
    ) -> QuerySet[Shift]:
        """
        Compiles a comprehensive, filtered collection of shifts within a tenant context.
        Supports text searches, status categorization filters, and dynamic ordering scales.
        """
        queryset = ShiftSelector.get_queryset().filter(company=company)

        # Apply status filtering if explicitly requested
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        # Map functional type filters against actual model booleans
        if shift_type is not None:
            if str(shift_type).lower() == "night":
                queryset = queryset.filter(is_night_shift=True)
            elif str(shift_type).lower() == "day":
                queryset = queryset.filter(is_night_shift=False)

        # Apply text search across name or description parameters using Q structures
        if search:
            search_query = str(search).strip()
            queryset = queryset.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query)
            )

        return queryset.order_by(ordering)

    @staticmethod
    def get_active_shifts(*, company: Any) -> QuerySet[Shift]:
        """
        Returns all active shifts for a specific company tenant.
        Used to populate operational frontend selection dropdowns.
        """
        return ShiftSelector.get_queryset().filter(company=company, is_active=True)

    # =====================================================
    # VALIDATION HELPERS
    # =====================================================

    @staticmethod
    def exists_with_name(*, company: Any, name: str, exclude_id: Optional[Any] = None) -> bool:
        """
        Predicate method checking name collisions within a company's schedule definitions.
        Supports excluding an explicit primary key ID during update mutation evaluations.
        """
        queryset = Shift.objects.filter(company=company, name__iexact=name.strip())
        
        if exclude_id is not None:
            queryset = queryset.exclude(id=exclude_id)
            
        return queryset.exists()

    @staticmethod
    def exists_with_code(*, company: Any, code: str, exclude_id: Optional[Any] = None) -> bool:
        """
        Predicate verification evaluating code configurations. Falls back cleanly 
        to name matching checks to accommodate structural fields within the current schema.
        """
        return ShiftSelector.exists_with_name(
            company=company, 
            name=code, 
            exclude_id=exclude_id
        )