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

        # Weekly trend (last 12 weeks)
        today = timezone.localtime(timezone.now()).date()
        weekly_trend = []
        for week_offset in range(11, -1, -1):
            week_start = today - datetime.timedelta(days=today.weekday() + (week_offset * 7))
            week_end = week_start + datetime.timedelta(days=6)
            week_records = DailyAttendanceSelector.get_date_range_records(
                membership=membership,
                start_date=week_start,
                end_date=week_end,
            )
            present_count = sum(1 for r in week_records if r.attendance_status == "PRESENT")
            total_count = week_records.count()
            weekly_trend.append({
                "week_start": week_start.strftime("%Y-%m-%d"),
                "week_end": week_end.strftime("%Y-%m-%d"),
                "present_days": present_count,
                "total_days": total_count,
                "percentage": round((present_count / total_count * 100), 2) if total_count > 0 else 0,
            })

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
    def build_detail_screen_payload(*, record_id: int, company: Company, membership: Membership) -> Dict[str, Any]:
        """Build detail screen with summary and timeline."""
        # Get the daily attendance record
        daily_record = DailyAttendanceSelector.get_by_id(record_id=record_id, company=company)
        if not daily_record:
            return {}

        # Get timeline events
        events = AttendanceEventSelector.get_events_for_membership_and_date(
            membership=membership,
            date=daily_record.attendance_date,
        )

        timeline = [
            {
                "event_type": event.event_type,
                "event_time": event.event_time.isoformat(),
                "attendance_method": event.attendance_method,
                "location_name": getattr(event.location, 'name', None) if event.location else None,
                "notes": event.notes,
            }
            for event in events
        ]

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
                "event_time": event.event_time.isoformat(),
                "attendance_method": event.attendance_method,
                "location_name": getattr(event.location, 'name', None) if event.location else None,
                "notes": event.notes,
            }
            for event in events
        ]
