# apps/attendance/services/hr_directory_service.py
import datetime
from django.db.models import Q, QuerySet
from rest_framework.exceptions import ValidationError
from apps.companies.models import Company
from apps.attendance.selectors.hr_directory_selector import HREmployeeDirectorySelector

class HREmployeeDirectoryService:
    """
    Orchestrates business verification parameters, applies advanced multi-field search 
    criteria, and handles sorting rules for the Employee Attendance Directory.
    """

    ALLOWED_SORT_FIELDS = {
        "employee_name": "user__first_name",
        "-employee_name": "-user__first_name",
        "department": "department__name",
        "-department": "-department__name",
        "check_in_time": "db_first_in",
        "-check_in_time": "-db_first_in",
        "working_duration": "db_work_min",
        "-working_duration": "-db_work_min",
        "late_minutes": "db_late_min",
        "-late_minutes": "-db_late_min",
        "overtime": "db_ot_min",
        "-overtime": "-db_ot_min",
        "attendance_status": "db_status",
        "-attendance_status": "-db_status",
        "current_state": "computed_current_state",
        "-current_state": "-computed_current_state"
    }

    @classmethod
    def compile_directory_dataset(
        cls, 
        *, 
        company: Company, 
        params: dict
    ) -> QuerySet:
        """
        Validates payload filter schemas, injects lookup criteria, 
        and applies structural sorting constraints to the query parameters.
        """
        target_date = params.get("date")
        if not target_date:
            raise ValidationError("A valid date parameter (YYYY-MM-DD) must be specified.")

        # 1. Fetch our highly optimized query graph template
        queryset = HREmployeeDirectorySelector.get_optimized_directory_queryset(
            company=company, 
            target_date=target_date
        )

        # 2. Apply Corporate Profile Status Filtering (Active vs Inactive Workforce)
        status_scope = params.get("employment_status", "ACTIVE")
        if status_scope == "ACTIVE":
            queryset = queryset.filter(is_active=True)
        elif status_scope == "INACTIVE":
            queryset = queryset.filter(is_active=False)

        # 3. Apply Multi-Field Search Criteria
        search_query = params.get("search")
        if search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__email__icontains=search_query) |
                Q(department__name__icontains=search_query)
            )

        # 4. Apply Structural Domain Aggregation Filters
        if params.get("department"):
            queryset = queryset.filter(department_id=params["department"])

        if params.get("shift_name"):
            queryset = queryset.filter(db_shift_name__iexact=params["shift_name"])

        if params.get("attendance_status"):
            queryset = queryset.filter(db_status=params["attendance_status"])

        if params.get("current_state"):
            queryset = queryset.filter(computed_current_state=params["current_state"])

        if params.get("needs_review"):
            review_flag = str(params["needs_review"]).lower() == "true"
            queryset = queryset.filter(db_needs_review=review_flag)

        if params.get("auto_closed"):
            closed_flag = str(params["auto_closed"]).lower() == "true"
            queryset = queryset.filter(db_auto_closed=closed_flag)

        if params.get("late_only"):
            queryset = queryset.filter(db_late_min__gt=0)

        if params.get("missing_checkout"):
            queryset = queryset.filter(db_first_in__isnull=False, db_last_out__isnull=True, db_auto_closed=False)

        # 5. Apply Dynamic Ordering Parameters
        ordering_param = params.get("ordering", "employee_name")
        db_sort_field = cls.ALLOWED_SORT_FIELDS.get(ordering_param, "user__first_name")
        queryset = queryset.order_by(db_sort_field)

        return queryset