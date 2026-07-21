# apps/attendance/services/attendance_report_service.py
"""
Attendance Report Service Layer

Orchestrates parameters evaluation and date transformations for the reports UI.
Maintains pure workflow separation entirely isolated from database transaction blocks.
"""

import datetime
import calendar
from typing import Dict, Any, Tuple
from rest_framework.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.companies.models import Company
from apps.attendance.selectors.attendance_report_selector import AttendanceReportSelector


class AttendanceReportService:
    """
    Coordinates and validates structural metadata for enterprise payroll data graphs.
    """

    @classmethod
    def compile_attendance_report(
        cls,
        *,
        company: Company,
        params: Dict[str, Any]
    ) -> Tuple[Any, Dict[str, Any], Dict[str, Any]]:
        """
        Processes parameter constraints, resolves periods, and queries the selector layer.
        """
        # 1. Resolve and parse temporal variables
        date_from, date_to = cls._resolve_date_boundaries(params)

        # 2. Enforce strict parameter validation rules
        cls._validate_filters(params, date_from, date_to)

        # 3. Normalize internal lookups filter packet maps
        filters = {
            "date_from": date_from,
            "date_to": date_to,
            "department_id": params.get("department_id"),
            "membership_id": params.get("membership_id"),
            "attendance_status": params.get("attendance_status"),
            "search": params.get("search"),
        }

        # Handle enterprise safe default sorting options
        allowed_sort_fields = [
            "name", "-name", "attendance_percentage", "-attendance_percentage",
            "total_work_hours", "-total_work_hours", "late_count", "-late_count"
        ]
        ordering = params.get("ordering", "user__first_name")
        if ordering not in allowed_sort_fields:
            if ordering == "name":
                ordering = "user__first_name"
            elif ordering == "-name":
                ordering = "-user__first_name"
            else:
                ordering = "user__first_name"

        # 4. Delegate to ORM selector layer
        queryset, summary = AttendanceReportSelector.get_report_data(
            company=company,
            filters=filters,
            ordering=ordering
        )

        # 5. Formulate unified filter payload metadata envelope
        filter_metadata = {
            "selected_month": params.get("month"),
            "selected_year": params.get("year"),
            "selected_department": params.get("department_id"),
            "date_from": date_from.strftime("%Y-%m-%d"),
            "date_to": date_to.strftime("%Y-%m-%d")
        }

        return queryset, summary, filter_metadata

    @classmethod
    def _resolve_date_boundaries(cls, params: Dict[str, Any]) -> Tuple[datetime.date, datetime.date]:
        """ Extracts or derives standard calendar ranges based on parameters payload. """
        month_str = params.get("month")
        year_str = params.get("year")
        date_from_str = params.get("date_from")
        date_to_str = params.get("date_to")

        # Context Scenario A: Explicit Year/Month provided
        if month_str and year_str:
            try:
                month = int(month_str)
                year = int(year_str)
                if not (1 <= month <= 12):
                    raise ValueError
            except ValueError:
                raise ValidationError({"month": [_("Invalid month or year structural parameter specified.")]})
            
            _, last_day = calendar.monthrange(year, month)
            return datetime.date(year, month, 1), datetime.date(year, month, last_day)

        # Context Scenario B: Explicit Custom Date Range targets specified
        if date_from_str and date_to_str:
            try:
                date_from = datetime.datetime.strptime(date_from_str, "%Y-%m-%d").date()
                date_to = datetime.datetime.strptime(date_to_str, "%Y-%m-%d").date()
                return date_from, date_to
            except ValueError:
                raise ValidationError({"date_from": [_("Dates must track cleanly matching YYYY-MM-DD format parameters.")]})

        # Context Scenario C: Default fallback context parameters (Current Month Dashboard view)
        today = datetime.date.today()
        _, last_day = calendar.monthrange(today.year, today.month)
        return datetime.date(today.year, today.month, 1), datetime.date(today.year, today.month, last_day)

    @classmethod
    def _validate_filters(cls, params: Dict[str, Any], date_from: datetime.date, date_to: datetime.date) -> None:
        """ Evaluates logic checks before database compilation triggers. """
        if date_from > date_to:
            raise ValidationError({"date_from": [_("Chronological error: Start boundary date limits cannot follow finish targets.")]})

        if params.get("department_id"):
            try:
                int(params["department_id"])
            except ValueError:
                raise ValidationError({"department_id": [_("Department reference context parameter token must be an integer.")]})

        if params.get("membership_id"):
            try:
                int(params["membership_id"])
            except ValueError:
                raise ValidationError({"membership_id": [_("Membership reference context parameter token must be an integer.")]})









            
