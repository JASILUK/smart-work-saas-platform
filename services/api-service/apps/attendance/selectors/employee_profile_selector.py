# apps/attendance/selectors/employee_profile_selector.py
"""
Employee Profile Selector

Single-responsibility selector for loading employee header metadata.
Optimized with select_related to avoid N+1 queries against User, Department,
and Role associations.

Enriched with real-time operational status computation derived from live events,
shift schedules, and calendar rules matching the Live Workforce state.
"""

import datetime
import zoneinfo
from django.db.models import Q, OuterRef, Subquery, Exists, Case, When, Value, CharField, BooleanField, IntegerField
from django.utils import timezone
from rest_framework.exceptions import NotFound

from apps.companies.models import Company, Membership
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceEventTypes
from apps.attendance.models.daily_attendance import DailyAttendance
from apps.attendance.models.shift import Shift, EmployeeShiftAssignment
from apps.attendance.selectors.holiday_selector import HolidaySelector


class EmployeeProfileSelector:
    """
    Loads enriched employee profile data for the attendance profile header.
    """

    @classmethod
    def get_employee_profile(
        cls,
        *,
        company: Company,
        membership_id: int,
    ) -> Membership:
        """
        Retrieves a Membership with all related profile data preloaded.

        Includes:
            - User (full_name, email, username, avatar)
            - Department (name)
            - Role (name)
            - Current real-time attendance status computed live for today
            - Last recorded attendance source channel

        Raises:
            NotFound: If the membership does not exist or does not belong
            to the company.
        """
        # 1. Determine local time/date context based on company timezone configuration
        company_tz_str = getattr(company, "timezone", "UTC")
        try:
            local_zone = zoneinfo.ZoneInfo(company_tz_str)
        except Exception:
            local_zone = zoneinfo.ZoneInfo("UTC")

        now_local = timezone.now().astimezone(local_zone)
        target_date = now_local.date()
        current_time_local = now_local.time()

        # 2. Time boundaries in UTC for filtering live events
        tz_default = timezone.get_default_timezone()
        start_local = datetime.datetime.combine(target_date, datetime.time.min)
        end_local = datetime.datetime.combine(target_date, datetime.time.max)
        start_utc = timezone.make_aware(start_local, tz_default).astimezone(timezone.utc)
        end_utc = timezone.make_aware(end_local, tz_default).astimezone(timezone.utc)

        # 3. Subqueries for live events
        latest_event_qs = AttendanceEvent.objects.filter(
            company=company, membership_id=OuterRef("pk"),
            event_time__range=(start_utc, end_utc)
        ).order_by("-event_time")

        first_in_qs = AttendanceEvent.objects.filter(
            company=company, membership_id=OuterRef("pk"),
            event_time__range=(start_utc, end_utc),
            event_type=AttendanceEventTypes.CHECK_IN
        ).order_by("event_time")

        # 4. Subqueries for shift assignment rules
        assignment_qs = EmployeeShiftAssignment.objects.filter(
            membership_id=OuterRef("pk"), is_active=True,
            effective_from__lte=target_date
        ).filter(
            Q(effective_until__isnull=True) | Q(effective_until__gte=target_date)
        ).order_by("-effective_from")

        general_shift_qs = Shift.objects.filter(
            company=company, name__iexact="General", is_active=True
        )

        # 5. Subqueries for calendar states (Leave & Holidays)
        from apps.attendance.models.leave import LeaveRequest
        approved_leave_qs = LeaveRequest.objects.filter(
            company=company, membership_id=OuterRef("pk"),
            status="approved",
            start_date__lte=target_date, end_date__gte=target_date
        )
        is_holiday = HolidaySelector.is_holiday(company=company, holiday_date=target_date)
        is_weekend = target_date.weekday() in [5, 6]

        # 6. Fallback historical source for source tracking field metadata
        historical_attendance = DailyAttendance.objects.filter(
            company=company, membership_id=OuterRef("pk")
        ).order_by("-attendance_date", "-created_at")

        try:
            employee = (
                Membership.objects.select_related(
                    "user",
                    "department",
                    "role",
                )
                .annotate(
                    # Live Event Annotations
                    evt_last_type=Subquery(latest_event_qs.values("event_type")[:1]),
                    evt_has_check_in=Exists(first_in_qs),
                    # Shift Schedule Annotations
                    has_direct_shift=Exists(assignment_qs),
                    has_general_shift=Exists(general_shift_qs),
                    shift_start=Case(
                        When(has_direct_shift=True, then=Subquery(assignment_qs.values("shift__start_time")[:1])),
                        When(has_general_shift=True, then=Subquery(general_shift_qs.values("start_time")[:1])),
                        default=Value(None),
                        output_field=CharField(null=True),
                    ),
                    has_shift=Case(
                        When(has_direct_shift=True, then=Value(True)),
                        When(has_general_shift=True, then=Value(True)),
                        default=Value(False),
                        output_field=BooleanField(),
                    ),
                    shift_started=Case(
                        When(shift_start__isnull=False, shift_start__lte=current_time_local, then=Value(True)),
                        default=Value(False),
                        output_field=BooleanField(),
                    ),
                    # Calendar State Annotations
                    is_on_leave=Exists(approved_leave_qs),
                    is_holiday_day=Value(is_holiday, output_field=BooleanField()),
                    is_weekend_day=Value(is_weekend, output_field=BooleanField()),
                    # Operational Context Real-time evaluation
                    current_attendance_status=Case(
                        When(is_on_leave=True, then=Value("LEAVE")),
                        When(is_holiday_day=True, then=Value("HOLIDAY")),
                        When(is_weekend_day=True, then=Value("WEEKEND")),
                        When(evt_last_type=AttendanceEventTypes.CHECK_OUT, then=Value("CHECKED_OUT")),
                        When(evt_last_type=AttendanceEventTypes.BREAK_OUT, then=Value("BREAK")),
                        When(evt_has_check_in=True, then=Value("WORKING")),
                        When(has_shift=True, shift_started=False, then=Value("NOT_STARTED")),
                        When(has_shift=False, then=Value("NOT_STARTED")),
                        default=Value("ABSENT"),
                        output_field=CharField(),
                    ),
                    current_attendance_source=Subquery(historical_attendance.values("source")[:1]),
                )
                .get(
                    id=membership_id,
                    company=company,
                    is_active=True,
                )
            )
        except Membership.DoesNotExist:
            raise NotFound(
                detail={
                    "employee": (
                        f"Employee profile matching identifier "
                        f"#{membership_id} was not found."
                    )
                }
            )

        return employee