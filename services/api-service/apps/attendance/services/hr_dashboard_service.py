# apps/attendance/services/hr_dashboard_service.py
import datetime
from django.utils import timezone
from apps.companies.models import Company
from apps.attendance.selectors.hr_dashboard_selector import HRDashboardSelector
from apps.attendance.selectors.hr_live_selector import HRLiveAttendanceSelector
from apps.attendance.selectors.hr_activity_selector import HRDashboardActivitySelector

class HRAttendanceDashboardOrchestratorService:
    """
    Orchestrates data fetching across specialized dashboard selectors.
    Assembles summaries, live feeds, and alerts into a unified dataset.
    """

    @classmethod
    def compile_complete_dashboard(cls, *, company: Company, target_date: datetime.date) -> dict:
        """
        Queries and compiles all required operational data components into a unified payload.
        """
        # 1. Global Overview Statistics Card Configurations
        overview_stats = HRDashboardSelector.get_todays_overview_stats(
            company=company, 
            target_date=target_date
        )

        # 2. Section Segment Breakdowns
        department_summary = HRDashboardSelector.get_department_summaries(
            company=company, 
            target_date=target_date
        )
        
        shift_summary = HRDashboardSelector.get_shift_summaries(
            company=company, 
            target_date=target_date
        )

        # 3. Live Active Records Stream
        live_workforce = HRLiveAttendanceSelector.get_live_active_workforce(
            company=company, 
            target_date=target_date
        )

        # 4. Transaction Activity Timeline Logging
        recent_activity = HRDashboardActivitySelector.get_recent_activity_events(
            company=company, 
            target_date=target_date, 
            limit=10
        )

        # 5. Core Operational Review Exception Feeds
        review_alerts = HRDashboardActivitySelector.get_dashboard_review_alerts(
            company=company, 
            target_date=target_date
        )

        return {
            "overview": overview_stats,
            "department_summary": department_summary,
            "shift_summary": shift_summary,
            "live_attendance": live_workforce,
            "recent_activity": recent_activity,
            "alerts": review_alerts
        }