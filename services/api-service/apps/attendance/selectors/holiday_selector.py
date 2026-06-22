import datetime
from typing import Optional
from django.db.models import QuerySet, Count, Q
from django.utils import timezone
from django.utils.timezone import localdate
from apps.attendance.models import Holiday


class HolidaySelector:
    """
    Unified access layer isolating holiday database operations and reporting telemetry queries.
    Encapsulated as a class matching existing selector design patterns cleanly.
    """

    # =====================================================
    # BASE QUERYSET
    # =====================================================

    @classmethod
    def get_queryset(cls) -> QuerySet[Holiday]:
        """
        Returns the foundational base queryset for all Holiday selector operations.
        
        PERFORMANCE OPTIMIZATION:
        - Uses select_related("company") to proactively fetch foreign key data via an 
          SQL INNER JOIN, completely eliminating N+1 query bottlenecks when accessing 
          tenant fields.
        - Explicitly orders records chronologically by holiday_date to match database indexing.
        """
        return Holiday.objects.select_related("company").order_by("holiday_date")

    # =====================================================
    # SINGLE OBJECT LOOKUPS
    # =====================================================

    @classmethod
    def get_by_id(cls, *, holiday_id: int) -> Optional[Holiday]:
        """
        Retrieves a single holiday by its primary key ID.
        Returns None if the record does not exist instead of throwing a generic ObjectDoesNotExist error.
        """
        try:
            return cls.get_queryset().get(id=holiday_id)
        except Holiday.DoesNotExist:
            return None

    @classmethod
    def get_company_holiday(cls, *, company, holiday_id: int) -> Optional[Holiday]:
        """
        Retrieves a specific holiday for an explicit company tenant context.
        
        PERFORMANCE OPTIMIZATION:
        - Utilizes the composite database lookup boundaries to guarantee cross-tenant 
          data isolation at the database layer.
        """
        try:
            return cls.get_queryset().get(company=company, id=holiday_id)
        except Holiday.DoesNotExist:
            return None

    # =====================================================
    # COMPANY HOLIDAY QUERIES
    # =====================================================

    @classmethod
    def get_company_holidays(cls, *, company) -> QuerySet[Holiday]:
        """
        Returns all registered historical, current, and future holidays assigned 
        to a specific company tenant.
        """
        return cls.get_queryset().filter(company=company)

    @classmethod
    def get_holiday_metrics(cls, queryset) -> dict:
        """
        Calculates aggregate operational metrics across a filtered holiday scope.
        Keeps database math out of the view layer.
        """
        today = localdate()
        return queryset.aggregate(
            total=Count("id"),
            paid=Count("id", filter=Q(is_paid=True)),
            half_day=Count("id", filter=Q(is_half_day=True)),
            upcoming=Count("id", filter=Q(holiday_date__gte=today))
        )

    @classmethod
    def get_upcoming_holidays(cls, *, company) -> QuerySet[Holiday]:
        """
        Returns all upcoming holidays occurring on or after the current calendar date
        to supply dashboard visibility widgets.
        """
        today = timezone.localdate()
        return cls.get_queryset().filter(company=company, holiday_date__gte=today)

    @classmethod
    def get_next_upcoming_holiday(cls, *, company, from_date: datetime.date) -> Optional[Holiday]:
        """
        Synthesized entry point matching dashboard orchestration contracts securely 
        to resolve the nearest future holiday event log.
        """
        return cls.get_queryset().filter(company=company, holiday_date__gte=from_date).order_by("holiday_date").first()

    @classmethod
    def get_holidays_between(cls, *, company, start_date: datetime.date, end_date: datetime.date) -> QuerySet[Holiday]:
        """
        Returns all holidays within an inclusive date range interval for leave 
        processing validations and timesheet calculation engines.
        """
        return cls.get_queryset().filter(
            company=company,
            holiday_date__range=(start_date, end_date)
        )

    # =====================================================
    # VALIDATION HELPERS
    # =====================================================

    @classmethod
    def holiday_exists(cls, *, company, holiday_date: datetime.date, name: str) -> bool:
        """
        Predicate evaluator confirming whether a duplicate holiday record exists.
        
        PERFORMANCE OPTIMIZATION:
        - Uses .exists() to perform a lightweight boolean lookup directly inside the database 
          engine, avoiding memory allocation overhead from instantiating complete model fields.
        """
        return cls.get_queryset().filter(
            company=company,
            holiday_date=holiday_date,
            name__iexact=name
        ).exists()

    @classmethod
    def get_holiday_by_date(cls, *, company, holiday_date: datetime.date) -> QuerySet[Holiday]:
        """
        Returns all holidays occurring on a specific single date to accurately evaluate
        cases where multiple specialized or regional holidays overlap concurrently.
        """
        return cls.get_queryset().filter(company=company, holiday_date=holiday_date)

    # =====================================================
    # ATTENDANCE SUPPORT
    # =====================================================

    @classmethod
    def is_holiday(cls, *, company, holiday_date: datetime.date) -> bool:
        """
        Predicate utility identifying whether a given calendar date acts as a holiday.
        Optimized via .exists() for lightning-fast batch processing sweeps.
        """
        return cls.get_queryset().filter(company=company, holiday_date=holiday_date).exists()

    @classmethod
    def is_paid_holiday(cls, *, company, holiday_date: datetime.date) -> bool:
        """
        Determines if a given calendar date has an active paid holiday configuration
        to accurately credit employee payroll parameters.
        """
        return cls.get_queryset().filter(
            company=company,
            holiday_date=holiday_date,
            is_paid=True
        ).exists()

    @classmethod
    def is_half_day_holiday(cls, *, company, holiday_date: datetime.date) -> bool:
        """
        Checks if any registered holiday assigned to this day is configured as a partial shift window, 
        alerting calculation layers to expect midday check-in event logs.
        """
        return cls.get_queryset().filter(
            company=company,
            holiday_date=holiday_date,
            is_half_day=True
        ).exists()

    # =====================================================
    # DASHBOARD / REPORT SUPPORT
    # =====================================================

    @classmethod
    def get_holidays_for_month(cls, *, company, year: int, month: int) -> QuerySet[Holiday]:
        """
        Fetches the targeted monthly scoped holiday matrix utilized by employee calendar UI 
        grids and manager reports.
        """
        return cls.get_queryset().filter(
            company=company,
            holiday_date__year=year,
            holiday_date__month=month
        )

    # =====================================================
    # EXTERNAL IMPORT SUPPORT
    # =====================================================

    @classmethod
    def get_by_external_id(cls, *, company, provider: str, external_id: str) -> Optional[Holiday]:
        """
        Resolves unique vendor signatures to guarantee data integration tracking.
        Prevents duplicate entries when running automated cron workers from external compliance systems.
        """
        try:
            return cls.get_queryset().get(
                company=company,
                provider=provider,
                external_id=external_id
            )
        except Holiday.DoesNotExist:
            return None