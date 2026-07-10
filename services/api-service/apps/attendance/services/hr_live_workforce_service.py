# apps/attendance/services/hr_live_workforce_service.py

import datetime
from typing import Optional
from django.db.models import QuerySet
from django.utils import timezone
import zoneinfo
from rest_framework.exceptions import ValidationError

from apps.companies.models import Company
from apps.attendance.selectors.hr_live_workforce_selector import HRLiveWorkforceSelector


class HRLiveWorkforceService:
    """
    Orchestrates Live Workforce business logic.
    Validates parameters, delegates to selector, applies filters and ordering.
    """

    @classmethod
    def _validate_date(cls, date_str: Optional[str]) -> datetime.date:
        if not date_str:
            return timezone.now().date()
        try:
            return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            raise ValidationError("Date parameter must be in YYYY-MM-DD format.")

    @classmethod
    def _validate_ordering(cls, ordering: Optional[str]) -> str:
        if not ordering:
            return "employee_name"
        allowed = set(HRLiveWorkforceSelector.ALLOWED_ORDERING.keys())
        if ordering not in allowed:
            raise ValidationError(
                f"Invalid ordering. Allowed: {', '.join(sorted(allowed))}"
            )
        return ordering

    @classmethod
    def _get_current_time_local(cls, company: Company, target_date: datetime.date) -> datetime.time:
        """Get current time in company timezone for time-aware status logic."""
        company_tz_str = getattr(company, "timezone", "UTC")
        try:
            local_zone = zoneinfo.ZoneInfo(company_tz_str)
        except Exception:
            local_zone = zoneinfo.ZoneInfo("UTC")
        now_local = timezone.now().astimezone(local_zone)
        if target_date == now_local.date():
            return now_local.time()
        return datetime.time(23, 59, 59)

    @classmethod
    def compile_live_workforce_dataset(cls, *, company: Company, params: dict) -> tuple:
        target_date = cls._validate_date(params.get("date"))
        ordering = cls._validate_ordering(params.get("ordering"))

        current_time_local = cls._get_current_time_local(company, target_date)

        # FIXED: Parameter name is current_time_local, not current_time
        queryset = HRLiveWorkforceSelector.get_live_workforce_queryset(
            company=company,
            target_date=target_date,
            current_time_local=current_time_local,  # ✅ FIXED
        )

        status = params.get("status")
        if status:
            queryset = HRLiveWorkforceSelector.apply_status_filter(queryset, status)

        department = params.get("department")
        if department:
            try:
                queryset = HRLiveWorkforceSelector.apply_department_filter(queryset, int(department))
            except (ValueError, TypeError):
                raise ValidationError("Department must be a valid integer ID.")

        shift = params.get("shift")
        if shift:
            try:
                queryset = HRLiveWorkforceSelector.apply_shift_filter(queryset, int(shift))
            except (ValueError, TypeError):
                raise ValidationError("Shift must be a valid integer ID.")

        search = params.get("search")
        if search:
            queryset = HRLiveWorkforceSelector.apply_search_filter(queryset, search)

        if str(params.get("needs_review", "")).lower() == "true":
            queryset = HRLiveWorkforceSelector.apply_needs_review_filter(queryset)

        if str(params.get("late_only", "")).lower() == "true":
            queryset = HRLiveWorkforceSelector.apply_late_only_filter(queryset)

        if str(params.get("missing_checkout", "")).lower() == "true":
            queryset = HRLiveWorkforceSelector.apply_missing_checkout_filter(queryset)

        if str(params.get("auto_closed", "")).lower() == "true":
            queryset = HRLiveWorkforceSelector.apply_auto_closed_filter(queryset)

        work_mode = params.get("work_mode")
        if work_mode:
            queryset = HRLiveWorkforceSelector.apply_work_mode_filter(queryset, work_mode)

        queryset = HRLiveWorkforceSelector.apply_ordering(queryset, ordering)

        summary = HRLiveWorkforceSelector.get_summary(queryset)
        filter_metadata = HRLiveWorkforceSelector.get_filter_metadata(
            company=company, target_date=target_date
        )

        return queryset, summary, filter_metadata