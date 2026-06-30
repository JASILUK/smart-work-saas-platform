from django.db import models
from typing import TypedDict, List, Dict, Any, Optional
import datetime

class HRAuditActionChoices(models.TextChoices):
    MANUAL_CORRECTION = "MANUAL_CORRECTION", "Manual Correction Event Injected"
    RECORD_FINALIZE = "RECORD_FINALIZE", "Attendance Record Finalized for Payroll"
    RECORD_UNLOCK = "RECORD_UNLOCK", "Attendance Record Unlocked for Modification"
    TIMELINE_REPROCESS = "TIMELINE_REPROCESS", "Chronological Timeline Reprocessed"

class DashboardSummaryStatsDict(TypedDict):
    present: int
    absent: int
    half_day: int
    late: int
    leave: int
    holiday: int
    weekend: int
    review_required: int

class DepartmentBreakdownDict(TypedDict):
    department_id: Optional[int]
    department_name: str
    present_count: int
    absent_count: int
    late_count: int

class ComprehensiveDashboardSummaryDict(TypedDict):
    statistics: DashboardSummaryStatsDict
    department_breakdown: List[DepartmentBreakdownDict]