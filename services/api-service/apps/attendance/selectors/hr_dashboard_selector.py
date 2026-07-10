# apps/attendance/selectors/hr_dashboard_selector.py

from django.utils import timezone
from django.db.models import (
    QuerySet, Q, Count, OuterRef, Subquery, Exists, F,
    Case, When, Value, CharField, IntegerField, BooleanField, TimeField
)
from django.conf import settings
import datetime

from apps.companies.models import Company, Membership
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceEventTypes
from apps.attendance.models.daily_attendance import DailyAttendance
from apps.attendance.models.shift import Shift, EmployeeShiftAssignment
from apps.attendance.selectors.holiday_selector import HolidaySelector


class HRDashboardSelector:
    """
    Eagerly evaluates company-wide live telemetry contexts using raw punch events 
    and date-effective shift assignments to eliminate N+1 processing loops.
    """

    @classmethod
    def _get_date_range_in_utc(cls, target_date: datetime.date, tz_name: str = None) -> tuple:
        tz = timezone.get_default_timezone() if not tz_name else timezone.pytz.timezone(tz_name)
        start_local = datetime.datetime.combine(target_date, datetime.time.min)
        end_local = datetime.datetime.combine(target_date, datetime.time.max)
        start_aware = timezone.make_aware(start_local, tz)
        end_aware = timezone.make_aware(end_local, tz)
        return (
            start_aware.astimezone(timezone.utc),
            end_aware.astimezone(timezone.utc)
        )

    @classmethod
    def get_active_memberships_queryset(cls, *, company: Company) -> QuerySet[Membership]:
        return Membership.objects.filter(company=company, is_active=True).select_related("user", "department")

    @classmethod
    def compile_live_state_annotations(cls, *, company: Company, target_date: datetime.date) -> dict:
        start_utc, end_utc = cls._get_date_range_in_utc(target_date)

        last_event_subquery = AttendanceEvent.objects.filter(
            company=company,
            membership=OuterRef("pk"),
            event_time__range=(start_utc, end_utc)
        ).order_by("-event_time")

        # Direct assignment query
        assignment_subquery = EmployeeShiftAssignment.objects.filter(
            membership=OuterRef("pk"),
            is_active=True,
            effective_from__lte=target_date
        ).filter(
            Q(effective_until__isnull=True) | Q(effective_until__gte=target_date)
        ).order_by("-effective_from")

        # General shift fallback query
        general_shift_qs = Shift.objects.filter(
            company=company, name__iexact="General", is_active=True
        )

        first_check_in_subquery = AttendanceEvent.objects.filter(
            company=company,
            membership=OuterRef("pk"),
            event_time__range=(start_utc, end_utc),
            event_type=AttendanceEventTypes.CHECK_IN
        ).order_by("event_time").values("event_time")

        # Approved leave check
        from apps.attendance.models.leave import LeaveRequest
        approved_leave_qs = LeaveRequest.objects.filter(
            company=company,
            membership=OuterRef("pk"),
            status="approved",
            start_date__lte=target_date,
            end_date__gte=target_date
        )

        # FIXED: shift_start_annotation must include General fallback
        # Use Case/When to pick direct assignment first, then General fallback
        return {
            "has_direct_shift": Exists(assignment_subquery),
            "active_shift_id": Subquery(assignment_subquery.values("shift__id")[:1]),
            "shift_name_annotation": Subquery(assignment_subquery.values("shift__name")[:1]),
            
            # FIXED: shift_start_annotation now falls back to General shift
            "shift_start_annotation": Case(
                When(
                    Exists(assignment_subquery),
                    then=Subquery(assignment_subquery.values("shift__start_time")[:1])
                ),
                When(
                    Exists(general_shift_qs),
                    then=Subquery(general_shift_qs.values("start_time")[:1])
                ),
                default=Value(None),
                output_field=TimeField(null=True),
            ),
            # FIXED: shift_end_annotation also needs fallback
            "shift_end_annotation": Case(
                When(
                    Exists(assignment_subquery),
                    then=Subquery(assignment_subquery.values("shift__end_time")[:1])
                ),
                When(
                    Exists(general_shift_qs),
                    then=Subquery(general_shift_qs.values("end_time")[:1])
                ),
                default=Value(None),
                output_field=TimeField(null=True),
            ),

            "has_general_shift": Exists(general_shift_qs),
            "has_shift": Exists(assignment_subquery) | Exists(general_shift_qs),

            "last_event_type": Subquery(last_event_subquery.values("event_type")[:1]),
            "last_event_time": Subquery(last_event_subquery.values("event_time")[:1]),
            "last_event_method": Subquery(last_event_subquery.values("attendance_method")[:1]),

            "first_in_time": Subquery(first_check_in_subquery[:1]),
            "has_check_in": Exists(AttendanceEvent.objects.filter(
                company=company,
                membership=OuterRef("pk"),
                event_time__range=(start_utc, end_utc),
                event_type=AttendanceEventTypes.CHECK_IN
            )),
            "has_check_out": Exists(AttendanceEvent.objects.filter(
                company=company,
                membership=OuterRef("pk"),
                event_time__range=(start_utc, end_utc),
                event_type=AttendanceEventTypes.CHECK_OUT
            )),
            "is_on_leave": Exists(approved_leave_qs),
        }

    @classmethod
    def get_dashboard_summary(cls, *, company: Company, target_date: datetime.date, current_time_local: datetime.time) -> dict:
        annotations = cls.compile_live_state_annotations(company=company, target_date=target_date)
        base_pool = cls.get_active_memberships_queryset(company=company).annotate(**annotations)

        aggregation = base_pool.aggregate(
            total_employees=Count("id"),
            scheduled_today=Count("id", filter=Q(has_shift=True)),
            checked_in=Count("id", filter=Q(has_check_in=True)),
            currently_working=Count("id", filter=Q(has_check_in=True, has_check_out=False) & ~Q(last_event_type=AttendanceEventTypes.BREAK_OUT)),
            on_break=Count("id", filter=Q(has_check_in=True, last_event_type=AttendanceEventTypes.BREAK_OUT)),
            checked_out=Count("id", filter=Q(has_check_out=True)),
            on_leave=Count("id", filter=Q(is_on_leave=True)),
            # FIXED: ABSENT now works because shift_start_annotation includes General fallback
            absent_until_now=Count("id", filter=Q(
                has_shift=True,
                has_check_in=False,
                is_on_leave=False,
                shift_start_annotation__isnull=False,
                shift_start_annotation__lt=current_time_local
            ))
        )

        total = aggregation["scheduled_today"] or 1
        present = aggregation["checked_in"] or 0
        attendance_pct = round((present / total) * 100.0, 2)

        is_today_holiday = HolidaySelector.is_holiday(company=company, holiday_date=target_date)
        is_today_off = target_date.weekday() in [5, 6]

        return {
            "total_employees": aggregation["total_employees"] or 0,
            "scheduled_today": aggregation["scheduled_today"] or 0,
            "checked_in": present,
            "currently_working": aggregation["currently_working"] or 0,
            "on_break": aggregation["on_break"] or 0,
            "checked_out": aggregation["checked_out"] or 0,
            "on_leave": aggregation["on_leave"] or 0,
            "absent_until_now": aggregation["absent_until_now"] or 0,
            "attendance_percentage": attendance_pct,
            "is_holiday": is_today_holiday,
            "is_off_day": is_today_off
        }

    @classmethod
    def get_department_summary(cls, *, company: Company, target_date: datetime.date, current_time_local: datetime.time) -> list:
        annotations = cls.compile_live_state_annotations(company=company, target_date=target_date)

        dept_summary = cls.get_active_memberships_queryset(company=company).annotate(**annotations).values(
            "department__id", "department__name"
        ).annotate(
            employees=Count("id"),
            working=Count("id", filter=Q(has_check_in=True, has_check_out=False) & ~Q(last_event_type=AttendanceEventTypes.BREAK_OUT)),
            on_break=Count("id", filter=Q(has_check_in=True, last_event_type=AttendanceEventTypes.BREAK_OUT)),
            checked_out=Count("id", filter=Q(has_check_out=True)),
            on_leave=Count("id", filter=Q(is_on_leave=True)),
            # FIXED: ABSENT now works because shift_start_annotation includes General fallback
            absent=Count("id", filter=Q(
                has_shift=True, has_check_in=False, is_on_leave=False,
                shift_start_annotation__isnull=False,
                shift_start_annotation__lt=current_time_local
            )),
            not_started=Count("id", filter=Q(
                has_shift=True, has_check_in=False, is_on_leave=False,
                shift_start_annotation__isnull=False,
                shift_start_annotation__gte=current_time_local
            ))
        )

        return [
            {
                "department_id": item["department__id"] or 0,
                "department_name": item["department__name"] or "Unassigned Department",
                "employees_count": item["employees"],
                "working_count": item["working"],
                "break_count": item["on_break"],
                "checked_out_count": item["checked_out"],
                "leave_count": item["on_leave"],
                "absent_count": item["absent"],
                "not_started_count": item["not_started"],
                "attendance_percentage": round(((item["employees"] - item["absent"]) / (item["employees"] or 1)) * 100, 2)
            }
            for item in dept_summary
        ]

    @classmethod
    def get_shift_summary(cls, *, company: Company, target_date: datetime.date, current_time_local: datetime.time) -> list:
        annotations = cls.compile_live_state_annotations(company=company, target_date=target_date)
        memberships_today = cls.get_active_memberships_queryset(company=company).annotate(**annotations)
        company_shifts = Shift.objects.filter(company=company, is_active=True)
        general_shift = company_shifts.filter(name__iexact="General").first()

        shift_summary_list = []
        for shift in company_shifts:
            if general_shift and shift.id == general_shift.id:
                shift_pool = memberships_today.filter(
                    Q(active_shift_id=shift.id) | 
                    Q(active_shift_id__isnull=True, has_general_shift=True)
                )
            else:
                shift_pool = memberships_today.filter(active_shift_id=shift.id)

            metrics = shift_pool.aggregate(
                employees=Count("id"),
                working=Count("id", filter=Q(has_check_in=True, has_check_out=False) & ~Q(last_event_type=AttendanceEventTypes.BREAK_OUT)),
                on_break=Count("id", filter=Q(has_check_in=True, last_event_type=AttendanceEventTypes.BREAK_OUT)),
                checked_out=Count("id", filter=Q(has_check_out=True)),
                on_leave=Count("id", filter=Q(is_on_leave=True)),
                absent=Count("id", filter=Q(
                    has_check_in=False, is_on_leave=False,
                    shift_start_annotation__isnull=False,
                    shift_start_annotation__lt=current_time_local
                )),
                late=Count("id", filter=Q(has_check_in=True, first_in_time__time__gt=shift.start_time))
            )

            # FIXED: Removed double-counting Python loop. 
            # The aggregation above already counts all employees in shift_pool correctly
            # because shift_start_annotation now includes General fallback.
            absent_count = metrics["absent"] or 0

            shift_summary_list.append({
                "shift_id": shift.id,
                "shift_name": shift.name,
                "employees_count": metrics["employees"] or 0,
                "working_count": metrics["working"] or 0,
                "break_count": metrics["on_break"] or 0,
                "checked_out_count": metrics["checked_out"] or 0,
                "leave_count": metrics["on_leave"] or 0,
                "absent_count": absent_count,
                "late_count": metrics["late"] or 0
            })

        return shift_summary_list

    @classmethod
    def get_live_workforce(cls, *, company: Company, target_date: datetime.date, current_time_local: datetime.time) -> list:
        annotations = cls.compile_live_state_annotations(company=company, target_date=target_date)
        pool = cls.get_active_memberships_queryset(company=company).annotate(**annotations).filter(
            last_event_type__isnull=False
        ).order_by("-last_event_time")[:20]

        result = []
        for mem in pool:
            status_str = "NOT_STARTED"
            
            if mem.is_on_leave:
                status_str = "LEAVE"
            elif mem.last_event_type == AttendanceEventTypes.CHECK_OUT:
                status_str = "CHECKED_OUT"
            elif mem.last_event_type == AttendanceEventTypes.BREAK_OUT:
                status_str = "BREAK"
            elif mem.has_check_in:
                status_str = "WORKING"
            elif mem.has_shift and mem.shift_start_annotation and mem.shift_start_annotation < current_time_local:
                status_str = "ABSENT"

            is_late_calculation = False
            if mem.has_check_in and mem.first_in_time and mem.shift_start_annotation:
                is_late_calculation = mem.first_in_time.time() > mem.shift_start_annotation

            result.append({
                "membership_id": mem.id,
                "full_name": mem.user.get_full_name(),
                "avatar_url": None,
                "department_name": mem.department.name if mem.department else "Unassigned",
                "shift_name": mem.shift_name_annotation or "General Shift",
                "last_event_type": mem.last_event_type,
                "last_event_time": mem.last_event_time,
                "current_status": status_str,
                "is_late": is_late_calculation
            })

        return result

    @classmethod
    def get_activity_feed(cls, *, company: Company, target_date: datetime.date) -> QuerySet[AttendanceEvent]:
        start_utc, end_utc = cls._get_date_range_in_utc(target_date)
        
        return AttendanceEvent.objects.filter(
            company=company,
            event_time__range=(start_utc, end_utc)
        ).select_related(
            "membership",
            "membership__user",
            "membership__department"
        ).order_by("-event_time")[:20]