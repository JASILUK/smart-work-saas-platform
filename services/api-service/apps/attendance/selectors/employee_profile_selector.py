# apps/attendance/selectors/employee_profile_selector.py
"""
Employee Profile Selector

Single-responsibility selector for loading employee header metadata.
Optimized with select_related to avoid N+1 queries against User, Department,
and Role associations.
"""

from django.db.models import OuterRef, Subquery

from rest_framework.exceptions import NotFound

from apps.companies.models import Company, Membership
from apps.attendance.models.daily_attendance import DailyAttendance


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
            - Current attendance status and source from the latest
              DailyAttendance record

        Raises:
            NotFound: If the membership does not exist or does not belong
            to the company.
        """

        latest_attendance = (
            DailyAttendance.objects.filter(
                company=company,
                membership_id=OuterRef("pk"),
            )
            .order_by("-attendance_date", "-created_at")
            .values("attendance_status", "source")[:1]
        )

        try:
            employee = (
                Membership.objects.select_related(
                    "user",
                    "department",
                    "role",
                )
                .annotate(
                    current_attendance_status=Subquery(
                        latest_attendance.values("attendance_status")
                    ),
                    current_attendance_source=Subquery(
                        latest_attendance.values("source")
                    ),
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