import datetime
from typing import Optional
from django.db.models import QuerySet
from apps.companies.models import Company, Membership
from apps.attendance.models.attendance_event import AttendanceEvent, AttendanceEventTypes


class AttendanceEventSelector:
    """
    Optimized data access selectors for Attendance Events.
    """
    @classmethod
    def get_queryset(cls) -> QuerySet[AttendanceEvent]:
        return AttendanceEvent.objects.select_related(
            "membership__user", "membership__department", "location", "face_enrollment"
        )

    @classmethod
    def get_by_id(cls, *, event_id: int, company: Company) -> Optional[AttendanceEvent]:
        return cls.get_queryset().filter(id=event_id, company=company).first()

    @classmethod
    def get_latest_event(cls, *, company: Company, membership: Membership, target_date: Optional[datetime.date] = None) -> Optional[AttendanceEvent]:
        """ Fetches the latest recorded punch card action for an employee profile. """
        queryset = cls.get_queryset().filter(company=company, membership=membership)
        if target_date:
            queryset = queryset.filter(event_time__date=target_date)
        return queryset.order_by("-event_time", "-id").first()

    @classmethod
    def get_today_events(cls, *, company: Company, membership: Membership) -> QuerySet[AttendanceEvent]:
        today_utc = timezone.now().date()
        return cls.get_queryset().filter(company=company, membership=membership, event_time__date=today_utc).order_by("event_time")

    @classmethod
    def get_membership_events(cls, *, company: Company, membership: Membership, start_date: datetime.date, end_date: datetime.date) -> QuerySet[AttendanceEvent]:
        return cls.get_queryset().filter(company=company, membership=membership, event_time__date__range=[start_date, end_date]).order_by("event_time")