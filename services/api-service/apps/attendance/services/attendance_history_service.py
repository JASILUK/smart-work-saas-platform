import datetime
from typing import Dict, List, Any, Optional
from django.utils import timezone
from apps.companies.models import Company, Membership
from apps.attendance.selectors.daily_attendance_selector import DailyAttendanceSelector
from apps.attendance.selectors.attendance_event_selector import AttendanceEventSelector


class AttendanceHistoryService:
    """
    Service layer for attendance history aggregation and payload building.
    Owns all business logic. Selectors only fetch data.
    """

    @staticmethod
    def build_employee_summary_cards(*, membership: Membership) -> Dict[str, Any]:
        """Build summary cards for employee dashboard."""
        today = timezone.localtime(timezone.now()).date()

        # Current month
        start_of_month = today.replace(day=1)
        month_summary = DailyAttendanceSelector.get_attendance_summary(
            membership=membership,
            date_from=start_of_month,
            date_to=today,
        )

        # Year to date
        start_of_year = today.replace(month=1, day=1)
        ytd_summary = DailyAttendanceSelector.get_attendance_summary(
            membership=membership,
            date_from=start_of_year,
            date_to=today,
        )

        # FIX #1: Add sparkline data for the 4 summary cards (last 7 days)
        spark_start = today - datetime.timedelta(days=6)
        spark_records = DailyAttendanceSelector.get_records_for_date_range(
            membership=membership,
            date_from=spark_start,
            date_to=today,
        )

        present_sparkline = []
        absent_sparkline = []
        late_sparkline = []
        percentage_sparkline = []
        running_present = 0
        running_total = 0

        for record in spark_records:
            is_present = 1 if record.attendance_status == "PRESENT" else 0
            is_absent = 1 if record.attendance_status == "ABSENT" else 0
            is_late = 1 if record.is_late else 0

            present_sparkline.append(is_present)
            absent_sparkline.append(is_absent)
            late_sparkline.append(is_late)

            running_present += is_present
            running_total += 1
            pct = round((running_present / running_total * 100), 1) if running_total > 0 else 0
            percentage_sparkline.append(pct)

        return {
            "current_month": {
                "present_days": month_summary["present_days"],
                "absent_days": month_summary["absent_days"],
                "late_days": month_summary["late_days"],
                "attendance_percentage": month_summary["attendance_percentage"],
                "total_work_hours": month_summary["total_work_hours"],
            },
            "year_to_date": {
                "present_days": ytd_summary["present_days"],
                "absent_days": ytd_summary["absent_days"],
                "late_days": ytd_summary["late_days"],
                "attendance_percentage": ytd_summary["attendance_percentage"],
                "total_work_hours": ytd_summary["total_work_hours"],
            },
            # FIX #1 (continued): Flattened keys for card sparklines
            "present_days": month_summary["present_days"],
            "absent_days": month_summary["absent_days"],
            "late_days": month_summary["late_days"],
            "attendance_percentage": month_summary["attendance_percentage"],
            "total_work_hours": month_summary["total_work_hours"],
            "total_days": month_summary["total_days"],
            "total_overtime_hours": month_summary.get("total_overtime_hours", 0),
            "present_sparkline": present_sparkline,
            "absent_sparkline": absent_sparkline,
            "late_sparkline": late_sparkline,
            "percentage_sparkline": percentage_sparkline,
        }

    @staticmethod
    def build_attendance_statistics(*, company: Company, date_from: Optional[datetime.date] = None, date_to: Optional[datetime.date] = None) -> Dict[str, Any]:
        """Build company-wide attendance statistics for managers."""
        return DailyAttendanceSelector.get_attendance_statistics(
            company=company,
            date_from=date_from,
            date_to=date_to,
        )

    @staticmethod
    def build_trend_graphs(*, membership: Membership, year: int) -> Dict[str, Any]:
        """Build weekly and monthly trend data."""
        monthly_trend = DailyAttendanceSelector.get_attendance_trend(
            membership=membership,
            year=year,
        )

        # FIX #2: Use get_weekly_records from selector instead of manual loop
        # This is more efficient and consistent
        weekly_trend = DailyAttendanceSelector.get_weekly_records(
            membership=membership,
            year=year,
        )

        return {
            "monthly": monthly_trend,
            "weekly": weekly_trend,
        }

    @staticmethod
    def build_calendar_payload(*, membership: Membership, year: int, month: int) -> List[Dict[str, Any]]:
        """Build calendar dataset for a given month."""
        return DailyAttendanceSelector.get_attendance_calendar_data(
            membership=membership,
            year=year,
            month=month,
        )

    @staticmethod
    def build_detail_screen_payload(*, record_id: int, company: Company, membership: Membership) -> Optional[Dict[str, Any]]:
        """Build detail screen with summary and timeline."""
        # FIX #3: Security check — ensure employee can only access their own records
        daily_record = DailyAttendanceSelector.get_by_id(record_id=record_id, company=company)
        if not daily_record or daily_record.membership_id != membership.id:
            return None

        # Get timeline events
        events = AttendanceEventSelector.get_events_for_membership_and_date(
            membership=membership,
            date=daily_record.attendance_date,
        )

        timeline = [
            {
                "event_type": event.event_type,
                "event_time": event.event_time.isoformat() if event.event_time else None,
                "attendance_method": event.attendance_method,
                "location_name": getattr(event.location, 'name', None) if event.location else None,
                "notes": event.notes or "",
            }
            for event in events
        ]

        # FIX #3 (continued): Sort timeline chronologically
        timeline.sort(key=lambda x: x["event_time"] or "")

        return {
            "daily_record": daily_record,
            "timeline": timeline,
        }

    @staticmethod
    def build_event_timeline(*, membership: Membership, date: datetime.date) -> List[Dict[str, Any]]:
        """Build event timeline for a specific date."""
        events = AttendanceEventSelector.get_events_for_membership_and_date(
            membership=membership,
            date=date,
        )

        return [
            {
                "event_type": event.event_type,
                "event_time": event.event_time.isoformat() if event.event_time else None,
                "attendance_method": event.attendance_method,
                "location_name": getattr(event.location, 'name', None) if event.location else None,
                "notes": event.notes or "",
            }
            for event in events
        ]