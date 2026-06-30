import datetime
from django.db.models import QuerySet, Q
from apps.companies.models import Company
from apps.attendance.models.attendance_event import AttendanceEvent
from apps.attendance.models.daily_attendance import DailyAttendance

class HRDashboardActivitySelector:
    """
    Fetches real-time timeline event streams and critical exceptions for the dashboard.
    """

    @classmethod
    def get_recent_activity_events(cls, *, company: Company, target_date: datetime.date, limit: int = 10) -> QuerySet[AttendanceEvent]:
        """
        Returns the latest transactional punches across the organization.
        Uses select_related to look up cross-domain relations in a single pass.
        """
        return AttendanceEvent.objects.filter(
            company=company,
            event_time__date=target_date
        ).select_related(
            "membership__user",
            "membership__department"
        ).order_by("-event_time")[:limit]

    @classmethod
    def get_dashboard_review_alerts(cls, *, company: Company, target_date: datetime.date) -> QuerySet[DailyAttendance]:
        """
        Isolates exceptional tracking conditions requiring administrative attention.
        """
        return DailyAttendance.objects.filter(
            company=company,
            attendance_date=target_date
        ).filter(
            Q(needs_review=True) | Q(is_auto_closed=True) | Q(attendance_status="REVIEW_REQUIRED")
        ).select_related(
            "membership__user",
            "membership__department"
        ).order_by("-total_work_minutes")