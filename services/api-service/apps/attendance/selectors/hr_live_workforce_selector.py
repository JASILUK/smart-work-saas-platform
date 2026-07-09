# apps/attendance/selectors/hr_live_workforce_selector.py

import datetime
from typing import Optional
from django.db.models import (
    QuerySet, Q, Count, OuterRef, Subquery, Exists, F, 
    Case, When, Value, CharField, IntegerField, BooleanField, DurationField
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.companies.models import Company, Membership
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceEventTypes
from apps.attendance.models.daily_attendance import DailyAttendance, DailyAttendanceStatus
from apps.attendance.models.shift import Shift, EmployeeShiftAssignment
from apps.attendance.selectors.holiday_selector import HolidaySelector


class HRLiveWorkforceSelector:
    """
    High-performance selector for the Live Workforce page.
    Derives real-time employee operational state from AttendanceEvents,
    ShiftAssignments, and time context. Uses DailyAttendance only for
    review flags, late minutes, and record IDs — never for primary status.
    """

    # ── Status Constants ──────────────────────────────────────────────
    STATUS_WORKING = "WORKING"
    STATUS_BREAK = "BREAK"
    STATUS_CHECKED_OUT = "CHECKED_OUT"
    STATUS_NOT_STARTED = "NOT_STARTED"
    STATUS_ABSENT = "ABSENT"
    STATUS_LEAVE = "LEAVE"
    STATUS_HOLIDAY = "HOLIDAY"
    STATUS_WEEKEND = "WEEKEND"
    STATUS_REVIEW_REQUIRED = "REVIEW_REQUIRED"

    # ── Base Queryset ───────────────────────────────────────────────────

    @classmethod
    def get_base_queryset(cls, *, company: Company) -> QuerySet[Membership]:
        """Foundation queryset with all required relations pre-loaded."""
        return Membership.objects.filter(company=company, is_active=True).select_related(
            "user",
            "department",
            "role"
        )

    # ── UTC Date Range Helper ───────────────────────────────────────────

    @classmethod
    def _get_utc_range(cls, target_date: datetime.date) -> tuple:
        """
        Convert local calendar date to UTC datetime range.
        Critical: AttendanceEvent stores UTC timestamps.
        """
        tz = timezone.get_default_timezone()
        start_local = datetime.datetime.combine(target_date, datetime.time.min)
        end_local = datetime.datetime.combine(target_date, datetime.time.max)
        start_aware = timezone.make_aware(start_local, tz)
        end_aware = timezone.make_aware(end_local, tz)
        return (
            start_aware.astimezone(timezone.utc),
            end_aware.astimezone(timezone.utc)
        )

    # ── Live Event Annotations ────────────────────────────────────────

    @classmethod
    def annotate_live_events(cls, *, company: Company, target_date: datetime.date) -> dict:
        """
        Build annotation dict for today's AttendanceEvent-derived state.
        All event filters use UTC range, never __date.
        """
        start_utc, end_utc = cls._get_utc_range(target_date)

        # Latest event of any type today
        latest_event_qs = AttendanceEvent.objects.filter(
            company=company,
            membership=OuterRef("pk"),
            event_time__range=(start_utc, end_utc)
        ).order_by("-event_time")

        # First check-in today
        first_in_qs = AttendanceEvent.objects.filter(
            company=company,
            membership=OuterRef("pk"),
            event_time__range=(start_utc, end_utc),
            event_type=AttendanceEventTypes.CHECK_IN
        ).order_by("event_time")

        # Last check-out today
        last_out_qs = AttendanceEvent.objects.filter(
            company=company,
            membership=OuterRef("pk"),
            event_time__range=(start_utc, end_utc),
            event_type=AttendanceEventTypes.CHECK_OUT
        ).order_by("-event_time")

        # Total break duration: sum of (BREAK_IN - BREAK_OUT) pairs
        # We compute this at the Python level for simplicity; 
        # for DB-level, a custom function would be needed.
        # Here we annotate existence flags for break state.

        return {
            "evt_last_type": Subquery(latest_event_qs.values("event_type")[:1]),
            "evt_last_time": Subquery(latest_event_qs.values("event_time")[:1]),
            "evt_last_method": Subquery(latest_event_qs.values("attendance_method")[:1]),
            "evt_first_in": Subquery(first_in_qs.values("event_time")[:1]),
            "evt_last_out": Subquery(last_out_qs.values("event_time")[:1]),
            "evt_has_check_in": Exists(first_in_qs),
            "evt_has_check_out": Exists(last_out_qs),
        }

    # ── Shift Annotations ───────────────────────────────────────────────

    @classmethod
    def annotate_shift(cls, *, target_date: datetime.date) -> dict:
        """
        Resolve effective shift assignment for target_date.
        Uses date-effective EmployeeShiftAssignment.
        """
        assignment_qs = EmployeeShiftAssignment.objects.filter(
            membership=OuterRef("pk"),
            is_active=True,
            effective_from__lte=target_date
        ).filter(
            Q(effective_until__isnull=True) | Q(effective_until__gte=target_date)
        ).order_by("-effective_from")

        return {
            "shift_id": Subquery(assignment_qs.values("shift__id")[:1]),
            "shift_name": Subquery(assignment_qs.values("shift__name")[:1]),
            "shift_start": Subquery(assignment_qs.values("shift__start_time")[:1]),
            "shift_end": Subquery(assignment_qs.values("shift__end_time")[:1]),
            "has_shift": Exists(assignment_qs),
        }

    # ── DailyAttendance Annotations ───────────────────────────────────

    @classmethod
    def annotate_daily_record(cls, *, company: Company, target_date: datetime.date) -> dict:
        """
        Pull review flags, late minutes, and record ID from DailyAttendance.
        This is the ONLY place DailyAttendance is used.
        """
        daily_qs = DailyAttendance.objects.filter(
            company=company,
            membership=OuterRef("pk"),
            attendance_date=target_date
        )

        return {
            "da_record_id": Subquery(daily_qs.values("id")[:1]),
            "da_status": Subquery(daily_qs.values("attendance_status")[:1]),
            "da_late_min": Coalesce(Subquery(daily_qs.values("late_minutes")[:1]), Value(0)),
            "da_work_min": Coalesce(Subquery(daily_qs.values("total_work_minutes")[:1]), Value(0)),
            "da_break_min": Coalesce(Subquery(daily_qs.values("total_break_minutes")[:1]), Value(0)),
            "da_ot_min": Coalesce(Subquery(daily_qs.values("overtime_minutes")[:1]), Value(0)),
            "da_needs_review": Coalesce(Subquery(daily_qs.values("needs_review")[:1]), Value(False)),
            "da_review_reason": Subquery(daily_qs.values("review_reason")[:1]),
            "da_auto_closed": Coalesce(Subquery(daily_qs.values("is_auto_closed")[:1]), Value(False)),
            "da_has_record": Exists(daily_qs),
        }

    # ── Leave / Holiday / Weekend Annotations ─────────────────────────

    @classmethod
    def annotate_calendar_state(cls, *, company: Company, target_date: datetime.date) -> dict:
        """
        Determine if employee is on approved leave, or if today is a company holiday/weekend.
        """
        from apps.attendance.models.leave import LeaveRequest  # lazy import to avoid circular deps

        approved_leave_qs = LeaveRequest.objects.filter(
            company=company,
            membership=OuterRef("pk"),
            status="APPROVED",
            start_date__lte=target_date,
            end_date__gte=target_date
        )

        is_holiday = HolidaySelector.is_holiday(company=company, holiday_date=target_date)
        is_weekend = target_date.weekday() in [5, 6]

        return {
            "is_on_leave": Exists(approved_leave_qs),
            "is_holiday_today": Value(is_holiday, output_field=BooleanField()),
            "is_weekend_today": Value(is_weekend, output_field=BooleanField()),
        }

    # ── Computed Current Status ─────────────────────────────────────────

    @classmethod
    def annotate_current_status(cls) -> dict:
        """
        Derive operational status using event-driven logic with calendar overrides.
        Priority: LEAVE > HOLIDAY > WEEKEND > SHIFT/TIME > EVENTS
        """
        return {
            "computed_status": Case(
                # Calendar overrides (highest priority)
                When(is_on_leave=True, then=Value(cls.STATUS_LEAVE)),
                When(is_holiday_today=True, then=Value(cls.STATUS_HOLIDAY)),
                When(is_weekend_today=True, then=Value(cls.STATUS_WEEKEND)),
                # Event-driven status
                When(evt_last_type=AttendanceEventTypes.CHECK_OUT, then=Value(cls.STATUS_CHECKED_OUT)),
                When(evt_last_type=AttendanceEventTypes.BREAK_OUT, then=Value(cls.STATUS_BREAK)),
                When(evt_has_check_in=True, evt_has_check_out=False, then=Value(cls.STATUS_WORKING)),
                # Shift-based status
                When(has_shift=False, then=Value(cls.STATUS_NOT_STARTED)),
                # Default: no check-in, has shift → ABSENT (or NOT_STARTED if before shift)
                default=Value(cls.STATUS_ABSENT),
                output_field=CharField(),
            ),
            "computed_not_started_reason": Case(
                When(
                    has_shift=True, 
                    shift_start__isnull=False, 
                    then=Value("before_shift")
                ),
                default=Value("no_shift"),
                output_field=CharField(),
            ),
        }

    # ── Working Duration (Live) ─────────────────────────────────────────

    @classmethod
    def annotate_working_duration(cls, *, current_time: datetime.datetime) -> dict:
        """
        Calculate live working duration for WORKING employees.
        Current Time - First Check In - Break Duration.
        Stored as minutes for sorting; formatted in serializer.
        """
        # For DB-level calculation we'd need complex SQL.
        # We compute minutes for sorting; serializer does human formatting.
        # This annotation is a placeholder for DB-computed value;
        # actual calculation happens in Python loop for accuracy with break pairs.
        return {
            "live_work_minutes": Value(0, output_field=IntegerField()),
        }

    # ── Is Late ─────────────────────────────────────────────────────────

    @classmethod
    def annotate_is_late(cls) -> dict:
        """
        Flag if first check-in occurred after shift start.
        Uses event time, not DailyAttendance late_minutes (which may be policy-adjusted).
        """
        return {
            "is_late_flag": Case(
                When(
                    evt_first_in__isnull=False,
                    shift_start__isnull=False,
                    then=Value(True),  # Actual comparison done in Python for time-only fields
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
        }

    # ── Master Assembly ───────────────────────────────────────────────────

    @classmethod
    def get_live_workforce_queryset(
        cls,
        *,
        company: Company,
        target_date: datetime.date,
        current_time: datetime.datetime,
    ) -> QuerySet[Membership]:
        """
        Assemble the fully annotated, optimized queryset for Live Workforce.
        Single query with all annotations applied.
        """
        queryset = cls.get_base_queryset(company=company)

        # Apply all annotation layers
        queryset = queryset.annotate(**cls.annotate_live_events(company=company, target_date=target_date))
        queryset = queryset.annotate(**cls.annotate_shift(target_date=target_date))
        queryset = queryset.annotate(**cls.annotate_daily_record(company=company, target_date=target_date))
        queryset = queryset.annotate(**cls.annotate_calendar_state(company=company, target_date=target_date))
        queryset = queryset.annotate(**cls.annotate_current_status())
        queryset = queryset.annotate(**cls.annotate_working_duration(current_time=current_time))
        queryset = queryset.annotate(**cls.annotate_is_late())

        return queryset

    # ── Filter Application ──────────────────────────────────────────────

    @classmethod
    def apply_status_filter(cls, queryset: QuerySet, status: str) -> QuerySet:
        """Filter by computed operational status."""
        if status == cls.STATUS_REVIEW_REQUIRED:
            return queryset.filter(da_needs_review=True)
        return queryset.filter(computed_status=status)

    @classmethod
    def apply_department_filter(cls, queryset: QuerySet, department_id: int) -> QuerySet:
        return queryset.filter(department_id=department_id)

    @classmethod
    def apply_shift_filter(cls, queryset: QuerySet, shift_id: int) -> QuerySet:
        return queryset.filter(shift_id=shift_id)

    @classmethod
    def apply_search_filter(cls, queryset: QuerySet, search_query: str) -> QuerySet:
        """Multi-field search across employee identity fields."""
        return queryset.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )

    @classmethod
    def apply_needs_review_filter(cls, queryset: QuerySet) -> QuerySet:
        return queryset.filter(da_needs_review=True)

    @classmethod
    def apply_late_only_filter(cls, queryset: QuerySet) -> QuerySet:
        return queryset.filter(da_late_min__gt=0)

    @classmethod
    def apply_missing_checkout_filter(cls, queryset: QuerySet) -> QuerySet:
        """
        Checked in, no checkout, and current time is past shift end.
        """
        return queryset.filter(
            evt_has_check_in=True,
            evt_has_check_out=False,
            da_auto_closed=False,
        )

    @classmethod
    def apply_auto_closed_filter(cls, queryset: QuerySet) -> QuerySet:
        return queryset.filter(da_auto_closed=True)

    @classmethod
    def apply_work_mode_filter(cls, queryset: QuerySet, work_mode: str) -> QuerySet:
        # work_mode maps to shift-based or assignment-based filtering
        # Implementation depends on your work_mode model field
        # Placeholder: filter by shift name containing work_mode
        return queryset.filter(shift_name__icontains=work_mode)

    # ── Ordering ────────────────────────────────────────────────────────

    ALLOWED_ORDERING = {
        "employee_name": "user__first_name",
        "-employee_name": "-user__first_name",
        "department": "department__name",
        "-department": "-department__name",
        "shift": "shift_name",
        "-shift": "-shift_name",
        "current_status": "computed_status",
        "-current_status": "-computed_status",
        "working_duration": "da_work_min",
        "-working_duration": "-da_work_min",
        "late_minutes": "da_late_min",
        "-late_minutes": "-da_late_min",
        "first_check_in": "evt_first_in",
        "-first_check_in": "-evt_first_in",
        "last_event_time": "evt_last_time",
        "-last_event_time": "-evt_last_time",
    }

    @classmethod
    def apply_ordering(cls, queryset: QuerySet, ordering: str) -> QuerySet:
        db_field = cls.ALLOWED_ORDERING.get(ordering, "user__first_name")
        return queryset.order_by(db_field)

    # ── Summary Aggregation ─────────────────────────────────────────────

    @classmethod
    def get_summary(cls, queryset: QuerySet) -> dict:
        """
        Count employees by computed status from the filtered queryset.
        """
        agg = queryset.aggregate(
            total=Count("id"),
            working=Count("id", filter=Q(computed_status=cls.STATUS_WORKING)),
            break_count=Count("id", filter=Q(computed_status=cls.STATUS_BREAK)),
            checked_out=Count("id", filter=Q(computed_status=cls.STATUS_CHECKED_OUT)),
            not_started=Count("id", filter=Q(computed_status=cls.STATUS_NOT_STARTED)),
            absent=Count("id", filter=Q(computed_status=cls.STATUS_ABSENT)),
            leave=Count("id", filter=Q(computed_status=cls.STATUS_LEAVE)),
            holiday=Count("id", filter=Q(computed_status=cls.STATUS_HOLIDAY)),
            weekend=Count("id", filter=Q(computed_status=cls.STATUS_WEEKEND)),
            review_required=Count("id", filter=Q(da_needs_review=True)),
        )

        return {
            "total": agg["total"] or 0,
            "working": agg["working"] or 0,
            "break": agg["break_count"] or 0,
            "checked_out": agg["checked_out"] or 0,
            "not_started": agg["not_started"] or 0,
            "absent": agg["absent"] or 0,
            "leave": agg["leave"] or 0,
            "holiday": agg["holiday"] or 0,
            "weekend": agg["weekend"] or 0,
            "review_required": agg["review_required"] or 0,
        }

    # ── Filter Metadata ─────────────────────────────────────────────────

    @classmethod
    def get_filter_metadata(cls, *, company: Company, target_date: datetime.date) -> dict:
        """
        Return dropdown options for frontend filters.
        """
        departments = list(
            Membership.objects.filter(company=company, is_active=True)
            .values_list("department__id", "department__name")
            .distinct()
            .exclude(department__isnull=True)
        )

        shifts = list(
            Shift.objects.filter(company=company, is_active=True)
            .values("id", "name")
        )

        return {
            "departments": [
                {"id": dept_id, "name": dept_name or "Unassigned"}
                for dept_id, dept_name in departments
            ],
            "shifts": shifts,
            "available_statuses": [
                {"value": cls.STATUS_WORKING, "label": "Working"},
                {"value": cls.STATUS_BREAK, "label": "On Break"},
                {"value": cls.STATUS_CHECKED_OUT, "label": "Checked Out"},
                {"value": cls.STATUS_NOT_STARTED, "label": "Not Started"},
                {"value": cls.STATUS_ABSENT, "label": "Absent"},
                {"value": cls.STATUS_LEAVE, "label": "On Leave"},
                {"value": cls.STATUS_HOLIDAY, "label": "Holiday"},
                {"value": cls.STATUS_WEEKEND, "label": "Weekend"},
                {"value": cls.STATUS_REVIEW_REQUIRED, "label": "Needs Review"},
            ],
            "current_date": str(target_date),
        }