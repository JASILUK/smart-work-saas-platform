# apps/attendance/services/hr_live_workforce_service.py

import datetime
from typing import Optional
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.companies.models import Company
from apps.attendance.selectors.hr_live_workforce_selector import HRLiveWorkforceSelector


class HRLiveWorkforceService:
    """
    Orchestrates Live Workforce business logic.
    Validates parameters, delegates to selector, applies filters and ordering.
    No database queries here — all query building happens in the selector.
    """

    # ── Parameter Validation ────────────────────────────────────────────

    @classmethod
    def _validate_date(cls, date_str: Optional[str]) -> datetime.date:
        """Parse and validate date parameter."""
        if not date_str:
            return timezone.now().date()

        try:
            parsed = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            return parsed
        except (ValueError, TypeError):
            raise ValidationError("Date parameter must be in YYYY-MM-DD format.")

    @classmethod
    def _validate_ordering(cls, ordering: Optional[str]) -> str:
        """Ensure ordering parameter is in the allowed set."""
        if not ordering:
            return "employee_name"

        allowed = set(HRLiveWorkforceSelector.ALLOWED_ORDERING.keys())
        if ordering not in allowed:
            raise ValidationError(
                f"Invalid ordering. Allowed: {', '.join(sorted(allowed))}"
            )
        return ordering

    # ── Main Compilation ────────────────────────────────────────────────

    @classmethod
    def compile_live_workforce_dataset(
        cls,
        *,
        company: Company,
        params: dict,
    ) -> tuple:
        """
        Build the complete Live Workforce dataset.

        Returns:
            (queryset, summary_dict, filter_metadata_dict)
        """
        # 1. Validate core parameters
        target_date = cls._validate_date(params.get("date"))
        ordering = cls._validate_ordering(params.get("ordering"))

        # 2. Resolve current time in local timezone for live calculations
        current_time = timezone.now()

        # 3. Get fully annotated base queryset
        queryset = HRLiveWorkforceSelector.get_live_workforce_queryset(
            company=company,
            target_date=target_date,
            current_time=current_time,
        )

        # 4. Apply status filter
        status = params.get("status")
        if status:
            queryset = HRLiveWorkforceSelector.apply_status_filter(queryset, status)

        # 5. Apply department filter
        department = params.get("department")
        if department:
            try:
                queryset = HRLiveWorkforceSelector.apply_department_filter(
                    queryset, int(department)
                )
            except (ValueError, TypeError):
                raise ValidationError("Department must be a valid integer ID.")

        # 6. Apply shift filter
        shift = params.get("shift")
        if shift:
            try:
                queryset = HRLiveWorkforceSelector.apply_shift_filter(
                    queryset, int(shift)
                )
            except (ValueError, TypeError):
                raise ValidationError("Shift must be a valid integer ID.")

        # 7. Apply search
        search = params.get("search")
        if search:
            queryset = HRLiveWorkforceSelector.apply_search_filter(queryset, search)

        # 8. Apply boolean flag filters
        if str(params.get("needs_review", "")).lower() == "true":
            queryset = HRLiveWorkforceSelector.apply_needs_review_filter(queryset)

        if str(params.get("late_only", "")).lower() == "true":
            queryset = HRLiveWorkforceSelector.apply_late_only_filter(queryset)

        if str(params.get("missing_checkout", "")).lower() == "true":
            queryset = HRLiveWorkforceSelector.apply_missing_checkout_filter(queryset)

        if str(params.get("auto_closed", "")).lower() == "true":
            queryset = HRLiveWorkforceSelector.apply_auto_closed_filter(queryset)

        # 9. Apply work mode filter
        work_mode = params.get("work_mode")
        if work_mode:
            queryset = HRLiveWorkforceSelector.apply_work_mode_filter(
                queryset, work_mode
            )

        # 10. Apply ordering
        queryset = HRLiveWorkforceSelector.apply_ordering(queryset, ordering)

        # 11. Compute summary from the FULL filtered set (before pagination)
        summary = HRLiveWorkforceSelector.get_summary(queryset)

        # 12. Fetch filter metadata
        filter_metadata = HRLiveWorkforceSelector.get_filter_metadata(
            company=company, target_date=target_date
        )

        return queryset, summary, filter_metadata