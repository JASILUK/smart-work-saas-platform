# apps/companies/selectors/DepartmentSelectors.py

from typing import Optional

from django.db.models import (
    Count,
    Prefetch,
    Q,
    QuerySet,
)

from apps.companies.models import (
    Department,
)

from apps.core.exceptions import (
    NotFoundError,
)


class DepartmentSelector:

    # =====================================================
    # ANNOTATE COUNTS
    # =====================================================

    @staticmethod
    def _annotate_counts(
        qs: QuerySet,
    ) -> QuerySet:

        return qs.annotate(

            children_count=Count(
                "children",
                distinct=True,
            ),

            member_count=Count(

                "members",

                filter=Q(
                    members__is_active=True,
                ),

                distinct=True,
            ),
        )

    # =====================================================
    # GET DEPARTMENT BY ID
    # =====================================================

    @classmethod
    def get_by_id(
        cls,
        department_id: int,
        company,
    ) -> Department:

        try:

            queryset = (
                Department.objects
                .filter(
                    pk=department_id,
                    company=company,
                )
                .select_related(
                    "parent",
                    "head",
                    "conversation",
                )
                .prefetch_related(

                    "members",

                    Prefetch(
                        "children",

                        queryset=cls._annotate_counts(

                            Department.objects.select_related(
                                "parent",
                                "head",
                            )
                        ),

                        to_attr="prefetched_children",
                    ),
                )
            )

            return cls._annotate_counts(
                queryset
            ).get()

        except Department.DoesNotExist:

            raise NotFoundError(
                f"Department {department_id} not found"
            )

    # =====================================================
    # BASIC GET
    # =====================================================

    @classmethod
    def get_by_id_basic(
        cls,
        department_id: Optional[int],
        company,
    ):

        if department_id is None:
            return None

        try:

            return (
                Department.objects
                .select_related(
                    "parent",
                    "head",
                    "conversation",
                )
                .get(
                    pk=department_id,
                    company=company,
                )
            )

        except Department.DoesNotExist:

            raise NotFoundError(
                f"Department {department_id} not found"
            )

    # =====================================================
    # LIST COMPANY DEPARTMENTS
    # =====================================================

    @classmethod
    def list_by_company(
        cls,
        company,
    ) -> QuerySet:

        queryset = (
            Department.objects
            .filter(
                company=company,
            )
            .select_related(
                "parent",
                "head",
                "conversation",
            )
            .prefetch_related(
                "members",
            )
            .order_by("name")
        )

        return cls._annotate_counts(
            queryset
        )

    # =====================================================
    # LIST CHILDREN
    # =====================================================

    @classmethod
    def list_children(
        cls,
        parent: Department,
    ) -> QuerySet:

        queryset = (
            Department.objects
            .filter(
                parent=parent,
            )
            .select_related(
                "parent",
                "head",
            )
        )

        return cls._annotate_counts(
            queryset
        )

    # =====================================================
    # NAME EXISTS
    # =====================================================

    @classmethod
    def exists_with_name(
        cls,
        company,
        name: str,
        exclude_id: Optional[int] = None,
    ) -> bool:

        queryset = (
            Department.objects.filter(

                company=company,

                name__iexact=name.strip(),
            )
        )

        if exclude_id:

            queryset = queryset.exclude(
                pk=exclude_id,
            )

        return queryset.exists()