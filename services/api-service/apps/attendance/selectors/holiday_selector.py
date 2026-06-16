import datetime
from typing import Optional
from django.db.models import QuerySet
from django.utils import timezone
from apps.attendance.models import Holiday


# =====================================================
# BASE QUERYSET
# =====================================================

def get_queryset() -> QuerySet[Holiday]:
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

def get_by_id(*, holiday_id: int) -> Optional[Holiday]:
    """
    Retrieves a single holiday by its primary key ID.
    Returns None if the record does not exist instead of throwing a generic ObjectDoesNotExist error.
    """
    try:
        return get_queryset().get(id=holiday_id)
    except Holiday.DoesNotExist:
        return None


def get_company_holiday(*, company, holiday_id: int) -> Optional[Holiday]:
    """
    Retrieves a specific holiday for an explicit company tenant context.
    
    PERFORMANCE OPTIMIZATION:
    - Utilizes the composite database lookup boundaries to guarantee cross-tenant 
      data isolation at the database layer.
    """
    try:
        return get_queryset().get(company=company, id=holiday_id)
    except Holiday.DoesNotExist:
        return None


# =====================================================
# COMPANY HOLIDAY QUERIES
# =====================================================

def get_company_holidays(*, company) -> QuerySet[Holiday]:
    """
    Returns all registered historical, current, and future holidays assigned 
    to a specific company tenant.
    """
    return get_queryset().filter(company=company)


def get_upcoming_holidays(*, company) -> QuerySet[Holiday]:
    """
    Returns all upcoming holidays occurring on or after the current calendar date
    to supply dashboard visibility widgets.
    """
    today = timezone.localdate()
    return get_queryset().filter(company=company, holiday_date__gte=today)


def get_holidays_between(*, company, start_date: datetime.date, end_date: datetime.date) -> QuerySet[Holiday]:
    """
    Returns all holidays within an inclusive date range interval for leave 
    processing validations and timesheet calculation engines.
    """
    return get_queryset().filter(
        company=company,
        holiday_date__range=(start_date, end_date)
    )


# =====================================================
# VALIDATION HELPERS
# =====================================================

def holiday_exists(*, company, holiday_date: datetime.date, name: str) -> bool:
    """
    Predicate evaluator confirming whether a duplicate holiday record exists.
    
    PERFORMANCE OPTIMIZATION:
    - Uses .exists() to perform a lightweight boolean lookup directly inside the database 
      engine, avoiding memory allocation overhead from instantiating complete model fields.
    """
    return get_queryset().filter(
        company=company,
        holiday_date=holiday_date,
        name__iexact=name
    ).exists()


def get_holiday_by_date(*, company, holiday_date: datetime.date) -> QuerySet[Holiday]:
    """
    Returns all holidays occurring on a specific single date to accurately evaluate
    cases where multiple specialized or regional holidays overlap concurrently.
    """
    return get_queryset().filter(company=company, holiday_date=holiday_date)


# =====================================================
# ATTENDANCE SUPPORT
# =====================================================

def is_holiday(*, company, holiday_date: datetime.date) -> bool:
    """
    Predicate utility identifying whether a given calendar date acts as a holiday.
    Optimized via .exists() for lightning-fast batch processing sweeps.
    """
    return get_queryset().filter(company=company, holiday_date=holiday_date).exists()


def is_paid_holiday(*, company, holiday_date: datetime.date) -> bool:
    """
    Determines if a given calendar date has an active paid holiday configuration
    to accurately credit employee payroll parameters.
    """
    return get_queryset().filter(
        company=company,
        holiday_date=holiday_date,
        is_paid=True
    ).exists()


def is_half_day_holiday(*, company, holiday_date: datetime.date) -> bool:
    """
    Checks if any registered holiday assigned to this day is configured as a partial shift window, 
    alerting calculation layers to expect midday check-in event logs.
    """
    return get_queryset().filter(
        company=company,
        holiday_date=holiday_date,
        is_half_day=True
    ).exists()


# =====================================================
# DASHBOARD / REPORT SUPPORT
# =====================================================

def get_holidays_for_month(*, company, year: int, month: int) -> QuerySet[Holiday]:
    """
    Fetches the targeted monthly scoped holiday matrix utilized by employee calendar UI 
    grids and manager reports.
    """
    return get_queryset().filter(
        company=company,
        holiday_date__year=year,
        holiday_date__month=month
    )


# =====================================================
# EXTERNAL IMPORT SUPPORT
# =====================================================

def get_by_external_id(*, company, provider: str, external_id: str) -> Optional[Holiday]:
    """
    Resolves unique vendor signatures to guarantee data integration tracking.
    Prevents duplicate entries when running automated cron workers from external compliance systems.
    """
    try:
        return get_queryset().get(
            company=company,
            provider=provider,
            external_id=external_id
        )
    except Holiday.DoesNotExist:
        return None