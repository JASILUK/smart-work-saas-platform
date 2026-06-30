import datetime
from django.db.models import QuerySet
from apps.companies.models import Company
from apps.attendance.models.daily_attendance import DailyAttendance

class HRLiveAttendanceSelector:
    """
    Isolates active runtime states for employees currently working on-site.
    """

    @classmethod
    def get_live_active_workforce(cls, *, company: Company, target_date: datetime.date) -> QuerySet[DailyAttendance]:
        """
        Returns active records where the employee is clocked in but has no checkout log.
        Optimized via select_related to fully eliminate nested user field lookup hits.
        """
        return DailyAttendance.objects.filter(
            company=company,
            attendance_date=target_date,
            first_check_in_at__isnull=False,
            last_check_out_at__isnull=True
        ).select_related(
            "membership__user",
            "membership__department"
        ).order_by("-first_check_in_at")