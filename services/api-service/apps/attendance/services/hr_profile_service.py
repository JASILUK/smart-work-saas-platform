# apps/attendance/services/hr_profile_service.py
import datetime
from django.utils import timezone
from django.utils.dateparse import parse_date
from apps.companies.selectors.Employee_selectors import EmployeeSelector
from rest_framework.exceptions import ValidationError, NotFound

# Core system imports
from apps.companies.models import Company
from apps.attendance.selectors.hr_profile_summary_selector import HREmployeeSummarySelector
from apps.attendance.selectors.hr_profile_record_selector import HRProfileRecordSelector

class HREmployeeProfileOrchestratorService:
    """
    Validates operational parameters and manages data compilation workflows
    across selectors for the single employee profile view.
    """

    @classmethod
    def validate_and_parse_filter_bounds(cls, query_params: dict) -> dict:
        """
        Validates date parameters, falling back to the current month's bounds if dates are missing.
        """
        now = timezone.now().date()
        first_day_of_month = now.replace(day=1)
        
        start_str = query_params.get("date_from")
        end_str = query_params.get("date_to")
        
        start_date = parse_date(start_str) if start_str else first_day_of_month
        end_date = parse_date(end_str) if end_str else now
        
        if not start_date or not end_date:
            raise ValidationError("Date filters must use the YYYY-MM-DD parameter format.")
            
        if start_date > end_date:
            raise ValidationError("The start_date boundary must precede the end_date parameter constraint.")

        return {
            "start_date": start_date,
            "end_date": end_date,
            "attendance_status": query_params.get("status"),
            "late_only": query_params.get("late") == "true",
            "needs_review": query_params.get("needs_review") == "true",
            "auto_closed": query_params.get("auto_closed") == "true",
            "search_notes": query_params.get("search_notes"),
            "ordering": query_params.get("ordering", "-attendance_date")
        }

    @classmethod
    def compile_employee_profile_dataset(cls, *, company: Company, membership_id: int, query_params: dict) -> dict:
        """
        Verifies employee profiles and assembles cards, matrices, and list references into a single dictionary.
        """
        # 1. Enforce object structural presence controls using your verified selector module
        try:
            employee = EmployeeSelector.get_employee(company=company, employee_id=membership_id)
        except Exception:
            raise NotFound(f"Employee profile matching identifier key #{membership_id} was not found.")

        # 2. Extract verified range configurations
        clean_filters = cls.validate_and_parse_filter_bounds(query_params)

        # 3. Compile top profile metrics and summaries
        summary_cards = HREmployeeSummarySelector.get_period_summary_cards(
            company=company,
            membership_id=membership_id,
            start_date=clean_filters["start_date"],
            end_date=clean_filters["end_date"]
        )

        # 4. Extract trend timelines
        charts_matrices = HREmployeeSummarySelector.get_trend_chart_matrices(
            company=company,
            membership_id=membership_id,
            start_date=clean_filters["start_date"],
            end_date=clean_filters["end_date"]
        )

        # 5. Build the list queryset statement for the paginator
        records_queryset = HRProfileRecordSelector.get_profile_records_queryset(
            company=company,
            membership_id=membership_id,
            filters=clean_filters
        )

        return {
            "employee": employee,
            "summary": summary_cards,
            "charts": charts_matrices,
            "records_queryset": records_queryset
        }