# =====================================================
# SELECTORS
# =====================================================
# apps/leave/selectors.py
# =====================================================

import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from django.db.models import QuerySet, Count, Q, Sum, F, OuterRef, Subquery, Exists
from django.utils import timezone
from apps.companies.models import Company, Membership
from apps.attendance.models.leave import LeaveType, LeaveBalance, LeaveRequest


class LeaveTypeSelector:
    """
    Optimized data access selectors for LeaveType records.
    """

    @classmethod
    def get_queryset(cls) -> QuerySet[LeaveType]:
        return LeaveType.objects.select_related("company")

    @classmethod
    def get_by_id(cls, *, leave_type_id: int, company: Company) -> Optional[LeaveType]:
        return cls.get_queryset().filter(id=leave_type_id, company=company).first()

    @classmethod
    def get_by_code(cls, *, code: str, company: Company) -> Optional[LeaveType]:
        return cls.get_queryset().filter(code=code, company=company).first()

    @classmethod
    def list_by_company(cls, *, company: Company) -> QuerySet[LeaveType]:
        return cls.get_queryset().filter(company=company).order_by("name")

    @classmethod
    def list_active_by_company(cls, *, company: Company) -> QuerySet[LeaveType]:
        return cls.get_queryset().filter(company=company, is_active=True).order_by("name")

    @classmethod
    def lookup_by_code(cls, *, code: str, company: Company) -> Optional[LeaveType]:
        return cls.get_queryset().filter(code__iexact=code, company=company).first()


class LeaveBalanceSelector:
    """
    Optimized data access selectors for LeaveBalance records.
    """

    @classmethod
    def get_queryset(cls) -> QuerySet[LeaveBalance]:
        return LeaveBalance.objects.select_related(
            "membership",
            "membership__user",
            "membership__department",
            "leave_type",
            "company",
        )

    @classmethod
    def get_by_id(cls, *, balance_id: int, company: Company) -> Optional[LeaveBalance]:
        return cls.get_queryset().filter(id=balance_id, company=company).first()

    @classmethod
    def get_by_membership_and_type(
        cls,
        *,
        membership: Membership,
        leave_type: LeaveType,
        leave_year: int,
    ) -> Optional[LeaveBalance]:
        return cls.get_queryset().filter(
            membership=membership,
            leave_type=leave_type,
            leave_year=leave_year,
            company=membership.company,
        ).first()

    @classmethod
    def get_employee_balances(
        cls,
        *,
        membership: Membership,
        leave_year: Optional[int] = None,
    ) -> QuerySet[LeaveBalance]:
        queryset = cls.get_queryset().filter(
            membership=membership,
            company=membership.company,
        )
        if leave_year:
            queryset = queryset.filter(leave_year=leave_year)
        return queryset.order_by("-leave_year", "leave_type__name")

    @classmethod
    def get_employee_balance_by_type(
        cls,
        *,
        membership: Membership,
        leave_type_id: int,
        leave_year: int,
    ) -> Optional[LeaveBalance]:
        return cls.get_queryset().filter(
            membership=membership,
            leave_type_id=leave_type_id,
            leave_year=leave_year,
            company=membership.company,
        ).first()

    @classmethod
    def list_company_balances(
        cls,
        *,
        company: Company,
        leave_year: Optional[int] = None,
        membership_id: Optional[int] = None,
        leave_type_id: Optional[int] = None,
    ) -> QuerySet[LeaveBalance]:
        queryset = cls.get_queryset().filter(company=company)
        if leave_year:
            queryset = queryset.filter(leave_year=leave_year)
        if membership_id:
            queryset = queryset.filter(membership_id=membership_id)
        if leave_type_id:
            queryset = queryset.filter(leave_type_id=leave_type_id)
        return queryset.order_by("-leave_year", "membership__user__last_name", "leave_type__name")

    @classmethod
    def get_employee_balance_lookup(
        cls,
        *,
        membership: Membership,
        leave_type: LeaveType,
        leave_year: int,
    ) -> Optional[LeaveBalance]:
        return cls.get_queryset().filter(
            membership=membership,
            leave_type=leave_type,
            leave_year=leave_year,
            company=membership.company,
        ).first()


class LeaveRequestSelector:
    """
    Optimized data access selectors for LeaveRequest records.
    """

    @classmethod
    def get_queryset(cls) -> QuerySet[LeaveRequest]:
        return LeaveRequest.objects.select_related(
            "membership",
            "membership__user",
            "membership__department",
            "leave_type",
            "approved_by",
            "approved_by__user",
            "company",
        )

    @classmethod
    def get_by_id(cls, *, request_id: int, company: Company) -> Optional[LeaveRequest]:
        return cls.get_queryset().filter(id=request_id, company=company).first()

    @classmethod
    def get_my_request_detail(
        cls,
        *,
        request_id: int,
        membership: Membership,
    ) -> Optional[LeaveRequest]:
        return cls.get_queryset().filter(
            id=request_id,
            membership=membership,
            company=membership.company,
        ).first()

    @classmethod
    def get_my_requests(
        cls,
        *,
        membership: Membership,
        status: Optional[str] = None,
        leave_type_id: Optional[int] = None,
        year: Optional[int] = None,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
    ) -> QuerySet[LeaveRequest]:
        queryset = cls.get_queryset().filter(
            membership=membership,
            company=membership.company,
        )
        if status:
            queryset = queryset.filter(status=status)
        if leave_type_id:
            queryset = queryset.filter(leave_type_id=leave_type_id)
        if year:
            queryset = queryset.filter(
                Q(start_date__year=year) | Q(end_date__year=year)
            )
        if date_from:
            queryset = queryset.filter(start_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(end_date__lte=date_to)
        return queryset.order_by("-created_at")

    @classmethod
    def get_company_requests(
        cls,
        *,
        company: Company,
        status: Optional[str] = None,
        leave_type_id: Optional[int] = None,
        membership_id: Optional[int] = None,
        department_id: Optional[int] = None,
        year: Optional[int] = None,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
    ) -> QuerySet[LeaveRequest]:
        queryset = cls.get_queryset().filter(company=company)
        if status:
            queryset = queryset.filter(status=status)
        if leave_type_id:
            queryset = queryset.filter(leave_type_id=leave_type_id)
        if membership_id:
            queryset = queryset.filter(membership_id=membership_id)
        if department_id:
            queryset = queryset.filter(membership__department_id=department_id)
        if year:
            queryset = queryset.filter(
                Q(start_date__year=year) | Q(end_date__year=year)
            )
        if date_from:
            queryset = queryset.filter(start_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(end_date__lte=date_to)
        return queryset.order_by("-created_at")

    @classmethod
    def get_pending_requests(cls, *, company: Company) -> QuerySet[LeaveRequest]:
        return cls.get_queryset().filter(
            company=company,
            status=LeaveRequest.Status.PENDING,
        ).order_by("created_at")

    @classmethod
    def get_approved_requests(cls, *, company: Company) -> QuerySet[LeaveRequest]:
        return cls.get_queryset().filter(
            company=company,
            status=LeaveRequest.Status.APPROVED,
        ).order_by("-created_at")

    @classmethod
    def get_rejected_requests(cls, *, company: Company) -> QuerySet[LeaveRequest]:
        return cls.get_queryset().filter(
            company=company,
            status=LeaveRequest.Status.REJECTED,
        ).order_by("-created_at")

    @classmethod
    def get_cancelled_requests(cls, *, company: Company) -> QuerySet[LeaveRequest]:
        return cls.get_queryset().filter(
            company=company,
            status=LeaveRequest.Status.CANCELLED,
        ).order_by("-created_at")

    @classmethod
    def get_employee_requests(
        cls,
        *,
        membership: Membership,
    ) -> QuerySet[LeaveRequest]:
        return cls.get_queryset().filter(
            membership=membership,
            company=membership.company,
        ).order_by("-created_at")

    @classmethod
    def get_overlapping_requests(
        cls,
        *,
        membership: Membership,
        start_date: datetime.date,
        end_date: datetime.date,
        exclude_id: Optional[int] = None,
    ) -> QuerySet[LeaveRequest]:
        queryset = cls.get_queryset().filter(
            membership=membership,
            company=membership.company,
            status__in=[
                LeaveRequest.Status.PENDING,
                LeaveRequest.Status.APPROVED,
            ],
        ).exclude(
            # Non-overlapping: existing ends before new starts OR existing starts after new ends
            Q(end_date__lt=start_date) | Q(start_date__gt=end_date)
        )
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset

    @classmethod
    def get_statistics(cls, *, company: Company) -> Dict[str, Any]:
        today = timezone.now().date()
        first_of_month = today.replace(day=1)

        base_qs = LeaveRequest.objects.filter(company=company)

        stats = base_qs.aggregate(
            pending_count=Count("id", filter=Q(status=LeaveRequest.Status.PENDING)),
            approved_count=Count("id", filter=Q(status=LeaveRequest.Status.APPROVED)),
            rejected_count=Count("id", filter=Q(status=LeaveRequest.Status.REJECTED)),
            cancelled_count=Count("id", filter=Q(status=LeaveRequest.Status.CANCELLED)),
            today_count=Count("id", filter=Q(start_date__lte=today, end_date__gte=today)),
            this_month_count=Count("id", filter=Q(start_date__gte=first_of_month)),
            total_days_approved=Sum(
                "total_days",
                filter=Q(status=LeaveRequest.Status.APPROVED),
            ),
        )

        return {
            "pending": stats["pending_count"] or 0,
            "approved": stats["approved_count"] or 0,
            "rejected": stats["rejected_count"] or 0,
            "cancelled": stats["cancelled_count"] or 0,
            "today": stats["today_count"] or 0,
            "this_month": stats["this_month_count"] or 0,
            "total_days_approved": stats["total_days_approved"] or Decimal("0.0"),
        }

    @classmethod
    def get_request_detail_for_hr(
        cls,
        *,
        request_id: int,
        company: Company,
    ) -> Optional[LeaveRequest]:
        return cls.get_queryset().filter(id=request_id, company=company).first()

