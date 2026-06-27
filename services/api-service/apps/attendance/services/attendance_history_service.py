import calendar
import datetime
from typing import Dict, List, Any, Optional
from django.utils import timezone
from apps.attendance.selectors.company_work_schedule_selector import CompanyWorkScheduleSelector
from apps.attendance.selectors.holiday_selector import HolidaySelector
from apps.companies.models import Company, Membership
from apps.attendance.selectors.daily_attendance_selector import DailyAttendanceSelector
from apps.attendance.selectors.attendance_event_selector import AttendanceEventSelector


# ─── Day name to number mapping ────────────────────────────────────────────────
DAY_NAME_MAP = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}


class AttendanceHistoryService:
    """
    Service layer for attendance history aggregation and payload building.
    Owns all business logic. Selectors only fetch data.
    """

    @staticmethod
    def build_employee_summary_cards(*, membership) -> Dict[str, Any]:
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

        # Sparkline: last 7 days
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
            is_late = 1 if getattr(record, 'is_late', False) else 0

            present_sparkline.append(is_present)
            absent_sparkline.append(is_absent)
            late_sparkline.append(is_late)

            running_present += is_present
            running_total += 1
            pct = round((running_present / running_total * 100), 1) if running_total > 0 else 0.0
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
            # Flattened for cards
            "present_days": month_summary["present_days"],
            "absent_days": month_summary["absent_days"],
            "late_days": month_summary["late_days"],
            "half_days": month_summary.get("half_days", 0),
            "leave_days": month_summary.get("leave_days", 0),
            "holiday_days": month_summary.get("holiday_days", 0),
            "weekend_days": month_summary.get("weekend_days", 0),
            "attendance_percentage": month_summary["attendance_percentage"],
            "total_work_hours": month_summary["total_work_hours"],
            "total_days": month_summary["total_days"],
            "total_overtime_hours": month_summary.get("total_overtime_hours", 0.0),
            # Sparklines
            "present_sparkline": present_sparkline,
            "absent_sparkline": absent_sparkline,
            "late_sparkline": late_sparkline,
            "percentage_sparkline": percentage_sparkline,
        }
    

    @staticmethod
    def build_filtered_summary(*, membership, date_from: Optional[datetime.date] = None, date_to: Optional[datetime.date] = None) -> Dict[str, Any]:
        """
        Build attendance summary for a custom date range.
        Used by MyAttendanceSummaryAPI when date filters are applied.
        """
        today = timezone.localtime(timezone.now()).date()
        
        # Fallback to current month if no range provided
        from_date = date_from or today.replace(day=1)
        to_date = date_to or today
        
        # Get summary for the range
        summary = DailyAttendanceSelector.get_attendance_summary(
            membership=membership,
            date_from=from_date,
            date_to=to_date,
        )
        
        # ── FIXED: Build sparkline window clamping against the upper bound of the parsed context range ──
        # Cap sparkline to ensure it never evaluates days beyond 'to_date' (or today)
        spark_days = min(7, (to_date - from_date).days + 1)
        
        # Ensure we always request a logical segment, preventing negative limits if date parameters become inverted
        if spark_days > 0:
            spark_start = to_date - datetime.timedelta(days=spark_days - 1)
        else:
            spark_start = to_date
            
        spark_records = DailyAttendanceSelector.get_records_for_date_range(
            membership=membership,
            date_from=spark_start,
            date_to=to_date,
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
            is_late = 1 if getattr(record, 'is_late', False) else 0
            
            present_sparkline.append(is_present)
            absent_sparkline.append(is_absent)
            late_sparkline.append(is_late)
            
            running_present += is_present
            running_total += 1
            pct = round((running_present / running_total * 100), 1) if running_total > 0 else 0.0
            percentage_sparkline.append(pct)
        
        return {
            # Core counts
            "total_days": summary.get("total_days", 0),
            "present_days": summary.get("present_days", 0),
            "absent_days": summary.get("absent_days", 0),
            "half_days": summary.get("half_days", 0),
            "late_days": summary.get("late_days", 0),
            "leave_days": summary.get("leave_days", 0),
            "holiday_days": summary.get("holiday_days", 0),
            "weekend_days": summary.get("weekend_days", 0),
            
            # Metrics
            "attendance_percentage": summary.get("attendance_percentage", 0.0),
            "total_work_hours": summary.get("total_work_hours", 0.0),
            "total_overtime_hours": summary.get("total_overtime_hours", 0.0),
            
            # Sparklines
            "present_sparkline": present_sparkline,
            "absent_sparkline": absent_sparkline,
            "late_sparkline": late_sparkline,
            "percentage_sparkline": percentage_sparkline,
            
            # Metadata
            "date_from": str(from_date),
            "date_to": str(to_date),
            "period_label": f"{from_date.strftime('%b %-d')} – {to_date.strftime('%b %-d, %Y')}",
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
    def build_trend_graphs(*, membership, year: int):
        monthly = DailyAttendanceSelector.get_attendance_trend(
            membership=membership,
            year=year,
        )
        weekly = DailyAttendanceSelector.get_weekly_records(
            membership=membership,
            year=year,
        )
        return {"year": year, "monthly": monthly, "weekly": weekly}
        
    
     

    @staticmethod
    def build_calendar_payload(*, membership, year: int, month: int) -> List[Dict[str, Any]]:

        company = membership.company
        _, last_day = calendar.monthrange(year, month)

        # 1. Fetch attendance records
        attendance_records = DailyAttendanceSelector.get_attendance_calendar_data(
            membership=membership, year=year, month=month
        )
        attendance_map = {r["date"]: r for r in attendance_records}

        # 2. Fetch holidays
        holidays = HolidaySelector.get_holidays_for_month(
            company=company, year=year, month=month
        )
        holiday_map = {
            h.holiday_date.strftime("%Y-%m-%d"): h.name
            for h in holidays
        }

        # 3. Fetch work schedule and parse weekend days
        work_schedule = CompanyWorkScheduleSelector.get_company_schedule(company=company)
        
        weekend_days = set()
        if work_schedule and work_schedule.weekend_days:
            for day in work_schedule.weekend_days:
                day_str = str(day).strip().lower()
                if day_str.isdigit():
                    weekend_days.add(int(day_str))
                elif day_str in DAY_NAME_MAP:
                    weekend_days.add(DAY_NAME_MAP[day_str])
        else:
            # Default: Saturday=5, Sunday=6 (Western)
            # Change to {4, 5} for Middle East (Friday, Saturday)
            weekend_days = {5, 6}

        # 4. Build ALL days of the month
        calendar_days = []
        for day_num in range(1, last_day + 1):
            current_date = datetime.date(year, month, day_num)
            date_str = current_date.strftime("%Y-%m-%d")
            day_of_week = current_date.weekday()  # Monday=0, Sunday=6

            is_weekend = day_of_week in weekend_days
            is_holiday = date_str in holiday_map
            holiday_name = holiday_map.get(date_str)

            # Priority: HOLIDAY > WEEKEND > attendance > NOT_MARKED
            if is_holiday:
                status = "HOLIDAY"
            elif is_weekend:
                status = "WEEKEND"
            elif date_str in attendance_map:
                status = attendance_map[date_str]["status"]
            else:
                status = "NOT_MARKED"

            record = attendance_map.get(date_str, {})

            calendar_days.append({
                "date": date_str,
                "day_of_month": day_num,
                "day_of_week": day_of_week,
                "is_weekend": is_weekend,
                "is_holiday": is_holiday,
                "holiday_name": holiday_name,
                "status": status,
                "is_late": record.get("is_late", False),
                "is_half_day": record.get("is_half_day", False),
                "is_leave": record.get("is_leave", False),
                "check_in": record.get("check_in"),
                "check_out": record.get("check_out"),
                "work_hours": record.get("work_hours"),
            })

        return calendar_days

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