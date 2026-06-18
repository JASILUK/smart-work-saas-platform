from typing import Optional, Union
from django.db.models import QuerySet, Q
from apps.companies.models import Company
from apps.attendance.models.attendance_location import AttendanceLocation


class AttendanceLocationSelector:
    """
    Handles read optimizations and filtering definitions for geofenced parameters.
    """

    @classmethod
    def get_queryset(cls) -> QuerySet[AttendanceLocation]:
        """ Standardizes performance pre-fetches for base objects lookup queries. """
        return AttendanceLocation.objects.select_related("company", "created_by")

    @classmethod
    def list_company_locations(
        cls, *, company: Company, active_only: Optional[bool] = None, search: Optional[str] = None
    ) -> QuerySet[AttendanceLocation]:
        """
        Fetches a filtered checklist of geofences tied to the matching tenant instance.
        """
        queryset = cls.get_queryset().filter(company=company)

        if active_only is True:
            queryset = queryset.filter(is_active=True)
        elif active_only is False:
            queryset = queryset.filter(is_active=False)

        if search:
            search_term = search.strip()
            queryset = queryset.filter(
                Q(name__icontains=search_term) | Q(address__icontains=search_term)
            )

        return queryset.order_by("name")

    @classmethod
    def get_by_id(cls, *, location_id: int, company: Company) -> Optional[AttendanceLocation]:
        """ Resolves a specific perimeter mapping target inside safe tenant spaces. """
        return cls.get_queryset().filter(id=location_id, company=company).first()