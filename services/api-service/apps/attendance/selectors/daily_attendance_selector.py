import datetime
from typing import Optional
from django.db.models import QuerySet
from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance

class DailyAttendanceSelector:
    """
    Isolates lookup matrices and database query pipelines for analytical view sets extraction.
    """
    @classmethod
    def get_queryset(cls) -> QuerySet[DailyAttendance]:
        return DailyAttendance.objects.select_related("company", "membership__user", "membership__department")

    @classmethod
    def get_by_id(cls, *, record_id: int, company: Company) -> Optional[DailyAttendance]:
        return cls.get_queryset().filter(id=record_id, company=company).first()

    @classmethod
    def get_for_employee_date(cls, *, company: Company, membership: Membership, target_date: datetime.date) -> Optional[DailyAttendance]:
        return cls.get_queryset().filter(company=company, membership=membership, attendance_date=target_date).first()

    @classmethod
    def get_record_by_employee_and_date(cls, *, membership: Membership, date: datetime.date) -> Optional[DailyAttendance]:
        """
        Synthesized entry point matching dashboard orchestration contracts securely.
        """
        return cls.get_queryset().filter(company=membership.company, membership=membership, attendance_date=date).first()

    @classmethod
    def get_employee_history(cls, *, company: Company, membership: Membership, start: datetime.date, end: datetime.date) -> QuerySet[DailyAttendance]:
        return cls.get_queryset().filter(company=company, membership=membership, attendance_date__range=[start, end]).order_by("-attendance_date")

    @classmethod
    def get_records_for_date_range(cls, *, membership: Membership, start_date: datetime.date, end_date: datetime.date) -> QuerySet[DailyAttendance]:
        """
        Aggregates sequential daily ledger snapshots to drive dashboard monthly metrics.
        """
        return cls.get_queryset().filter(company=membership.company, membership=membership, attendance_date__range=[start_date, end_date]).order_by("attendance_date")

    @classmethod
    def get_company_attendance(cls, *, company: Company, target_date: datetime.date) -> QuerySet[DailyAttendance]:
        return cls.get_queryset().filter(company=company, attendance_date=target_date)

    @classmethod
    def get_pending_reviews(cls, *, company: Company) -> QuerySet[DailyAttendance]:
        return cls.get_queryset().filter(company=company, needs_review=True)

    @classmethod
    def get_unfinalized_records(cls, *, company: Company, start: datetime.date, end: datetime.date) -> QuerySet[DailyAttendance]:
        return cls.get_queryset().filter(company=company, attendance_date__range=[start, end], finalized_at__isnull=True)