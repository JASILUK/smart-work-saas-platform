# apps/attendance/selectors/hr_live_workforce_selector.py

import datetime
from typing import Optional
from django.db.models import (
    QuerySet, Q, Count, OuterRef, Subquery, Exists, F,
    Case, When, Value, CharField, IntegerField, BooleanField
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
    review flags, late minutes, and record IDs.
    """

    STATUS_WORKING = "WORKING"
    STATUS_BREAK = "BREAK"
    STATUS_CHECKED_OUT = "CHECKED_OUT"
    STATUS_NOT_STARTED = "NOT_STARTED"
    STATUS_ABSENT = "ABSENT"
    STATUS_LEAVE = "LEAVE"
    STATUS_HOLIDAY = "HOLIDAY"
    STATUS_WEEKEND = "WEEKEND"
    STATUS_REVIEW_REQUIRED = "REVIEW_REQUIRED"

    @classmethod
    def get_base_queryset(cls, *, company: Company) -> QuerySet[Membership]:
        return Membership.objects.filter(company=company, is_active=True).select_related(
            "user", "department", "role"
        )

    @classmethod
    def _get_utc_range(cls, target_date: datetime.date) -> tuple:
        tz = timezone.get_default_timezone()
        start_local = datetime.datetime.combine(target_date, datetime.time.min)
        end_local = datetime.datetime.combine(target_date, datetime.time.max)
        start_aware = timezone.make_aware(start_local, tz)
        end_aware = timezone.make_aware(end_local, tz)
        return (
            start_aware.astimezone(timezone.utc),
            end_aware.astimezone(timezone.utc)
        )

    @classmethod
    def annotate_live_events(cls, *, company: Company, target_date: datetime.date) -> dict:
        start_utc, end_utc = cls._get_utc_range(target_date)

        latest_event_qs = AttendanceEvent.objects.filter(
            company=company, membership=OuterRef("pk"),
            event_time__range=(start_utc, end_utc)
        ).order_by("-event_time")

        first_in_qs = AttendanceEvent.objects.filter(
            company=company, membership=OuterRef("pk"),
            event_time__range=(start_utc, end_utc),
            event_type=AttendanceEventTypes.CHECK_IN
        ).order_by("event_time")

        last_out_qs = AttendanceEvent.objects.filter(
            company=company, membership=OuterRef("pk"),
            event_time__range=(start_utc, end_utc),
            event_type=AttendanceEventTypes.CHECK_OUT
        ).order_by("-event_time")

        return {
            "evt_last_type": Subquery(latest_event_qs.values("event_type")[:1]),
            "evt_last_time": Subquery(latest_event_qs.values("event_time")[:1]),
            "evt_last_method": Subquery(latest_event_qs.values("attendance_method")[:1]),
            "evt_first_in": Subquery(first_in_qs.values("event_time")[:1]),
            "evt_last_out": Subquery(last_out_qs.values("event_time")[:1]),
            "evt_has_check_in": Exists(first_in_qs),
            "evt_has_check_out": Exists(last_out_qs),
        }

    @classmethod
    def annotate_shift(cls, *, company: Company, target_date: datetime.date, current_time_local: datetime.time) -> dict:
        assignment_qs = EmployeeShiftAssignment.objects.filter(
            membership=OuterRef("pk"), is_active=True,
            effective_from__lte=target_date
        ).filter(
            Q(effective_until__isnull=True) | Q(effective_until__gte=target_date)
        ).order_by("-effective_from")

        general_shift_qs = Shift.objects.filter(
            company=company, name__iexact="General", is_active=True
        )

        return {
            "direct_shift_id": Subquery(assignment_qs.values("shift__id")[:1]),
            "has_direct_shift": Exists(assignment_qs),

            "general_shift_id": Subquery(general_shift_qs.values("id")[:1]),
            "has_general_shift": Exists(general_shift_qs),

            "shift_id": Case(
                When(has_direct_shift=True, then=Subquery(assignment_qs.values("shift__id")[:1])),
                When(has_general_shift=True, then=Subquery(general_shift_qs.values("id")[:1])),
                default=Value(None),
                output_field=IntegerField(null=True),
            ),
            "shift_name": Case(
                When(has_direct_shift=True, then=Subquery(assignment_qs.values("shift__name")[:1])),
                When(has_general_shift=True, then=Value("General")),
                default=Value("Unassigned Shift"),
                output_field=CharField(),
            ),
            "shift_start": Case(
                When(has_direct_shift=True, then=Subquery(assignment_qs.values("shift__start_time")[:1])),
                When(has_general_shift=True, then=Subquery(general_shift_qs.values("start_time")[:1])),
                default=Value(None),
                output_field=CharField(null=True),
            ),
            "shift_end": Case(
                When(has_direct_shift=True, then=Subquery(assignment_qs.values("shift__end_time")[:1])),
                When(has_general_shift=True, then=Subquery(general_shift_qs.values("end_time")[:1])),
                default=Value(None),
                output_field=CharField(null=True),
            ),
            "has_shift": Case(
                When(has_direct_shift=True, then=Value(True)),
                When(has_general_shift=True, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
            "shift_started": Case(
                When(shift_start__isnull=False, shift_start__lte=current_time_local, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        }

    @classmethod
    def annotate_daily_record(cls, *, company: Company, target_date: datetime.date) -> dict:
        daily_qs = DailyAttendance.objects.filter(
            company=company, membership=OuterRef("pk"), attendance_date=target_date
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

    @classmethod
    def annotate_calendar_state(cls, *, company: Company, target_date: datetime.date) -> dict:
        from apps.attendance.models.leave import LeaveRequest

        approved_leave_qs = LeaveRequest.objects.filter(
            company=company, membership=OuterRef("pk"),
            status="approved",
            start_date__lte=target_date, end_date__gte=target_date
        )

        is_holiday = HolidaySelector.is_holiday(company=company, holiday_date=target_date)
        is_weekend = target_date.weekday() in [5, 6]

        return {
            "is_on_leave": Exists(approved_leave_qs),
            "is_holiday": Value(is_holiday, output_field=BooleanField()),
            "is_weekend": Value(is_weekend, output_field=BooleanField()),
        }

    @classmethod
    def annotate_current_status(cls, *, current_time_local: datetime.time) -> dict:
        """
        FIXED: Check leave BEFORE absent. Priority:
        LEAVE > HOLIDAY > WEEKEND > CHECK_OUT > BREAK > WORKING > NOT_STARTED > ABSENT
        """
        return {
            "computed_status": Case(
                # Calendar overrides (highest priority)
                When(is_on_leave=True, then=Value(cls.STATUS_LEAVE)),
                When(is_holiday=True, then=Value(cls.STATUS_HOLIDAY)),
                When(is_weekend=True, then=Value(cls.STATUS_WEEKEND)),
                # Event-driven status
                When(evt_last_type=AttendanceEventTypes.CHECK_OUT, then=Value(cls.STATUS_CHECKED_OUT)),
                When(evt_last_type=AttendanceEventTypes.BREAK_OUT, then=Value(cls.STATUS_BREAK)),
                When(evt_has_check_in=True, evt_has_check_out=False, then=Value(cls.STATUS_WORKING)),
                # Shift-based: if shift hasn't started yet, NOT_STARTED
                When(has_shift=True, shift_started=False, then=Value(cls.STATUS_NOT_STARTED)),
                # No shift at all
                When(has_shift=False, then=Value(cls.STATUS_NOT_STARTED)),
                # Has shift, shift started, no check-in, not on leave = ABSENT
                default=Value(cls.STATUS_ABSENT),
                output_field=CharField(),
            ),
        }

    @classmethod
    def annotate_working_duration(cls) -> dict:
        return {
            "live_work_minutes": Value(0, output_field=IntegerField()),
        }

    @classmethod
    def get_live_workforce_queryset(
        cls, *, company: Company, target_date: datetime.date, current_time_local: datetime.time
    ) -> QuerySet[Membership]:
        queryset = cls.get_base_queryset(company=company)
        queryset = queryset.annotate(**cls.annotate_live_events(company=company, target_date=target_date))
        queryset = queryset.annotate(**cls.annotate_shift(company=company, target_date=target_date, current_time_local=current_time_local))
        queryset = queryset.annotate(**cls.annotate_daily_record(company=company, target_date=target_date))
        queryset = queryset.annotate(**cls.annotate_calendar_state(company=company, target_date=target_date))
        queryset = queryset.annotate(**cls.annotate_current_status(current_time_local=current_time_local))
        queryset = queryset.annotate(**cls.annotate_working_duration())
        return queryset

    @classmethod
    def apply_status_filter(cls, queryset: QuerySet, status: str) -> QuerySet:
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
        return queryset.filter(
            evt_has_check_in=True, evt_has_check_out=False, da_auto_closed=False,
        )

    @classmethod
    def apply_auto_closed_filter(cls, queryset: QuerySet) -> QuerySet:
        return queryset.filter(da_auto_closed=True)

    @classmethod
    def apply_work_mode_filter(cls, queryset: QuerySet, work_mode: str) -> QuerySet:
        return queryset.filter(work_mode=work_mode)

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

    @classmethod
    def get_summary(cls, queryset: QuerySet) -> dict:
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

    @classmethod
    def get_filter_metadata(cls, *, company: Company, target_date: datetime.date) -> dict:
        departments = list(
            Membership.objects.filter(company=company, is_active=True)
            .values_list("department__id", "department__name")
            .distinct().exclude(department__isnull=True)
        )
        shifts = list(Shift.objects.filter(company=company, is_active=True).values("id", "name"))
        return {
            "departments": [{"id": did, "name": dname or "Unassigned"} for did, dname in departments],
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