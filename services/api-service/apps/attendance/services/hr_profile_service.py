# apps/attendance/services/hr_profile_service.py
"""
HR Employee Profile Service

Orchestrates the compilation of employee attendance profile data by coordinating
between dedicated selectors. Contains zero direct database queries — all data
access is delegated to selector layers.

Responsibilities:
    - Validate and normalize incoming query parameters
    - Load employee profile via EmployeeProfileSelector
    - Load summary KPIs via AttendanceSummarySelector
    - Load trend charts via AttendanceTrendSelector
    - Load status distribution via AttendanceTrendSelector
    - Build filtered record queryset via AttendanceRecordSelector
    - Compose the final response bundle with metadata
"""

import datetime
from typing import Dict, Any

from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError, NotFound

from apps.companies.models import Company
from apps.attendance.selectors.employee_profile_selector import EmployeeProfileSelector
from apps.attendance.selectors.attendance_summary_selector import AttendanceSummarySelector
from apps.attendance.selectors.attendance_trend_selector import AttendanceTrendSelector
from apps.attendance.selectors.attendance_record_selector import AttendanceRecordSelector


class HREmployeeProfileService:
    """
    Service coordinator for the HR Employee Attendance Profile endpoint.
    """

    # ------------------------------------------------------------------
    # Filter Validation
    # ------------------------------------------------------------------

    @classmethod
    def validate_and_parse_filter_bounds(cls, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates date range parameters and normalizes boolean filter flags.

        Defaults:
            date_from -> First day of current month
            date_to   -> Today

        Raises:
            ValidationError: On invalid date format, start > end, or future-only ranges.
        """
        today = timezone.now().date()
        first_day_of_month = today.replace(day=1)

        start_str = query_params.get("date_from")
        end_str = query_params.get("date_to")

        start_date = parse_date(start_str) if start_str else first_day_of_month
        end_date = parse_date(end_str) if end_str else today

        if not start_date or not end_date:
            raise ValidationError(
                detail={"date_filters": "Date filters must use the YYYY-MM-DD parameter format."}
            )

        if start_date > end_date:
            raise ValidationError(
                detail={"date_range": "The start_date boundary must precede the end_date parameter constraint."}
            )

        if start_date > today:
            raise ValidationError(
                detail={"date_range": "Future date ranges are not permitted."}
            )

        return {
            "start_date": start_date,
            "end_date": end_date,
            "attendance_status": query_params.get("attendance_status"),
            "late_only": query_params.get("late_only") == "true",
            "needs_review": query_params.get("needs_review") == "true",
            "auto_closed": query_params.get("auto_closed") == "true",
            "missing_checkout": query_params.get("missing_checkout") == "true",
            "holiday_only": query_params.get("holiday_only") == "true",
            "weekend_only": query_params.get("weekend_only") == "true",
            "leave_only": query_params.get("leave_only") == "true",
            "search_notes": query_params.get("search_notes"),
            "ordering": query_params.get("ordering", "-attendance_date")
        }

    # ------------------------------------------------------------------
    # Main Orchestration
    # ------------------------------------------------------------------

    @classmethod
    def compile_profile_dataset(
        cls,
        *,
        company: Company,
        membership_id: int,
        query_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compiles the complete employee attendance profile dataset.

        Returns:
            dict: Structured bundle containing employee, summary, charts,
                  status_distribution, records_queryset, and metadata.
        """
        # 1. Validate and normalize filter parameters
        clean_filters = cls.validate_and_parse_filter_bounds(query_params)

        # 2. Load employee profile (raises NotFound if absent)
        employee = EmployeeProfileSelector.get_employee_profile(
            company=company,
            membership_id=membership_id
        )

        # 3. Load summary KPIs
        summary = AttendanceSummarySelector.get_period_summary(
            company=company,
            membership_id=membership_id,
            start_date=clean_filters["start_date"],
            end_date=clean_filters["end_date"]
        )

        # 4. Load trend charts (daily, weekly, monthly + specific trend lines)
        charts = AttendanceTrendSelector.get_trend_charts(
            company=company,
            membership_id=membership_id,
            start_date=clean_filters["start_date"],
            end_date=clean_filters["end_date"]
        )

        # 5. Load status distribution
        status_distribution = AttendanceTrendSelector.get_status_distribution(
            company=company,
            membership_id=membership_id,
            start_date=clean_filters["start_date"],
            end_date=clean_filters["end_date"]
        )

        # 6. Build filtered record queryset (pagination applied in view)
        records_queryset = AttendanceRecordSelector.get_profile_records_queryset(
            company=company,
            membership_id=membership_id,
            filters=clean_filters
        )

        # 7. Compose metadata envelope
        metadata = {
            "date_from": clean_filters["start_date"].isoformat(),
            "date_to": clean_filters["end_date"].isoformat(),
            "generated_at": timezone.now().isoformat(),
            "filters": {
                k: v for k, v in clean_filters.items()
                if k not in ("start_date", "end_date") and v is not None and v is not False
            }
        }

        return {
            "employee": employee,
            "summary": summary,
            "charts": charts,
            "status_distribution": status_distribution,
            "records_queryset": records_queryset,
            "metadata": metadata
        }