from typing import Optional

from django.db.models import Count, Prefetch, Q, QuerySet

from apps.companies.models import Department
from apps.core.exceptions import NotFoundError


class DepartmentSelector:
    """Read-only queries for departments with N+1 prevention."""

    @staticmethod
    def _annotate_counts(qs: QuerySet) -> QuerySet:
        return qs.annotate(
            children_count=Count("children", distinct=True),
            member_count=Count(
                "membership_set",
                filter=Q(membership_set__is_active=True),
                distinct=True,
            ),
        )

    @classmethod
    def get_by_id(cls, department_id: int, company) -> Department:
        try:
            return cls._annotate_counts(
                Department.objects.filter(pk=department_id, company=company)
                .select_related("parent")
                .prefetch_related(
                    Prefetch(
                        "children",
                        queryset=cls._annotate_counts(
                            Department.objects.select_related("parent")
                        ),
                        to_attr="prefetched_children",
                    )
                )
            ).get()
        except Department.DoesNotExist:
            raise NotFoundError(f"Department {department_id} not found")

    @classmethod
    def get_by_id_basic(cls, department_id: Optional[int], company):
        if department_id is None:
            return None

        try:
            return Department.objects.get(pk=department_id, company=company)
        except Department.DoesNotExist:
            return None

    @classmethod
    def list_by_company(cls, company) -> QuerySet:
        return cls._annotate_counts(
            Department.objects.filter(company=company).select_related("parent")
        ).order_by("name")

    @classmethod
    def list_children(cls, parent: Department) -> QuerySet:
        return cls._annotate_counts(Department.objects.filter(parent=parent))

    @classmethod
    def exists_with_name(
        cls, company, name: str, exclude_id: Optional[int] = None
    ) -> bool:
        qs = Department.objects.filter(company=company, name__iexact=name.strip())

        if exclude_id:
            qs = qs.exclude(pk=exclude_id)

        return qs.exists()
