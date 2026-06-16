from typing import Any, Optional
from django.db.models import QuerySet
from apps.attendance.models import AttendancePolicy


class AttendancePolicySelector:
    """
    Selector class handling all read-only database queries and value resolutions
    for the AttendancePolicy model. Acts as the core configuration engine for daily 
    timesheet, shift-overtime, and payroll threshold scoring rules.
    """

    # =====================================================
    # BASE QUERYSET
    # =====================================================

    @staticmethod
    def get_queryset() -> QuerySet[AttendancePolicy]:
        """
        Returns the optimized base queryset for Attendance Policy lookups.
        
        PERFORMANCE OPTIMIZATION:
        - Selects active items by default to streamline target workspace parsing.
        """
        return AttendancePolicy.objects.filter(is_active=True)

    # =====================================================
    # CORE OBJECT LOOKUPS
    # =====================================================

    @staticmethod
    def get_by_company(*, company: Any) -> Optional[AttendancePolicy]:
        """
        Retrieves the active AttendancePolicy instance assigned to a specific company model entity.
        Returns None if no policy matches or if it is marked inactive.
        """
        return AttendancePolicySelector.get_queryset().filter(company=company).first()

    @staticmethod
    def get_by_company_id(*, company_id: Any) -> Optional[AttendancePolicy]:
        """
        Retrieves the active AttendancePolicy utilizing a raw company database primary key ID.
        Used widely by lifecycle web APIs and background tasks where full models aren't instantiated.
        """
        return AttendancePolicySelector.get_queryset().filter(company_id=company_id).first()

    @staticmethod
    def has_policy(*, company: Any) -> bool:
        """
        Predicate method identifying whether a specific company has an active rule policy configured.
        Optimized via .exists() to run memory-efficient validation boundaries inside the database engine.
        """
        return AttendancePolicySelector.get_queryset().filter(company=company).exists()

    # =====================================================
    # PERFORMANCE HELPERS (VALUE RESOLUTIONS)
    # =====================================================

    @staticmethod
    def get_required_work_minutes(*, company: Any) -> Optional[int]:
        """
        Convenience query helper resolving the mandatory daily operational workspace duration goal.
        Utilizes .values_list() to prevent full object inflation and save processing overhead.
        """
        policy_data = AttendancePolicySelector.get_queryset().filter(
            company=company
        ).values_list("required_work_minutes", flat=True).first()
        
        return policy_data if policy_data is not None else None

    @staticmethod
    def get_half_day_threshold(*, company: Any) -> Optional[int]:
        """
        Resolves the absolute threshold minute floor below which a shift tracking record 
        automatically gets downgraded into a partial or half-day calculation bucket.
        """
        policy_data = AttendancePolicySelector.get_queryset().filter(
            company=company
        ).values_list("half_day_below_minutes", flat=True).first()
        
        return policy_data if policy_data is not None else None

    @staticmethod
    def get_late_threshold(*, company: Any) -> Optional[int]:
        """
        Resolves the allowed flexibility grace window (in minutes) past a shift's start time 
        before an entry log triggers an automated 'Late Arrival' payroll exception tag.
        """
        policy_data = AttendancePolicySelector.get_queryset().filter(
            company=company
        ).values_list("late_after_minutes", flat=True).first()
        
        return policy_data if policy_data is not None else None

    @staticmethod
    def get_early_exit_threshold(*, company: Any) -> Optional[int]:
        """
        Resolves the threshold parameter tracking if an employee checkout timestamp constitutes 
        an unapproved early departure or early exit structural break flag.
        """
        policy_data = AttendancePolicySelector.get_queryset().filter(
            company=company
        ).values_list("early_exit_before_minutes", flat=True).first()
        
        return policy_data if policy_data is not None else None

    # =====================================================
    # POLICY STATUS PREDICATES
    # =====================================================

    @staticmethod
    def is_overtime_enabled(*, company: Any) -> bool:
        """
        Determines whether the target company tenant processes overtime increments on top of standard shifts.
        Falls back cleanly to returning False if no active rule model is found.
        """
        policy_data = AttendancePolicySelector.get_queryset().filter(
            company=company
        ).values_list("overtime_enabled", flat=True).first()
        
        return bool(policy_data)

    @staticmethod
    def is_regularization_enabled(*, company: Any) -> bool:
        """
        Identifies whether employees under this tenant can file retrospective attendance correction requests
        or shift log adjustments to fix missing clock-in events.
        """
        policy_data = AttendancePolicySelector.get_queryset().filter(
            company=company
        ).values_list("attendance_regularization_enabled", flat=True).first()
        
        return bool(policy_data) if policy_data is not None else False

    @staticmethod
    def is_auto_absent_enabled(*, company: Any) -> bool:
        """
        Confirms whether the automated scheduler engine should mark missing or unrecorded shift dates
        as an unexcused absence line item during payroll finalization sweeps.
        """
        policy_data = AttendancePolicySelector.get_queryset().filter(
            company=company
        ).values_list("auto_absent_if_no_checkin", flat=True).first()
        
        return bool(policy_data)