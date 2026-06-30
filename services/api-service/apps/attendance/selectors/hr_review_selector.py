import datetime
from django.db.models import QuerySet, Q, Count, Case, When, Value, CharField, F
from apps.companies.models import Company
from apps.attendance.models.daily_attendance import DailyAttendance, DailyAttendanceStatus
from apps.attendance.constants.hr_review_constants import HRReviewStatus, HRReviewPriority, HRAnomalyType

class HRAttendanceReviewSelector:
    """
    Isolates problematic attendance records across large tenant groups.
    Computes priority tokens dynamically using low-level database constraints.
    """

    @classmethod
    def get_review_queue_queryset(cls, *, company: Company, target_date: Optional[datetime.date] = None) -> QuerySet[DailyAttendance]:
        """
        Queries and returns records matching active exception patterns.
        Automatically skips clean data lines to protect system performance.
        """
        queryset = DailyAttendance.objects.filter(company=company).select_related(
            "membership__user",
            "membership__department",
            "finalized_by"
        )

        if target_date:
            queryset = queryset.filter(attendance_date=target_date)

        # 1. Filter out clean logs and narrow lookups strictly to problematic sheets
        queryset = queryset.filter(
            Q(needs_review=True) | Q(is_auto_closed=True) | Q(attendance_status="REVIEW_REQUIRED")
        )

        # 2. Annotate Anomaly Category classifications inside the database
        queryset = queryset.annotate(
            computed_anomaly_type=Case(
                When(is_auto_closed=True, then=Value(HRAnomalyType.AUTO_CLOSED)),
                When(first_check_in_at__isnull=False, last_check_out_at__isnull=True, then=Value(HRAnomalyType.MISSING_CHECKOUT)),
                When(is_late=True, late_minutes__gt=60, then=Value(HRAnomalyType.LATE_ARRIVAL)),
                default=Value(HRAnomalyType.REVIEW_REQUIRED),
                output_field=CharField()
            )
        )

        # 3. Annotate Priority weight profiles dynamically based on severity indicators
        queryset = queryset.annotate(
            computed_priority=Case(
                When(is_auto_closed=True, needs_review=True, then=Value(HRReviewPriority.CRITICAL)),
                When(first_check_in_at__isnull=False, last_check_out_at__isnull=True, then=Value(HRReviewReason.MISSING_CHECKOUT)),
                When(is_late=True, late_minutes__gt=60, then=Value(HRReviewPriority.HIGH)),
                default=Value(HRReviewPriority.MEDIUM),
                output_field=CharField()
            )
        )

        # 4. Generate dynamic status indicators matching your dashboard requirements
        queryset = queryset.annotate(
            computed_review_status=Case(
                When(finalized_at__isnull=False, then=Value(HRReviewStatus.RESOLVED)),
                When(finalized_at__isnull=True, finalized_by__isnull=False, then=Value(HRReviewStatus.IN_REVIEW)),
                default=Value(HRReviewStatus.PENDING),
                output_field=CharField()
            )
        )

        return queryset

    @classmethod
    def get_queue_dashboard_metrics(cls, *, company: Company) -> dict:
        """
        Assembles compliance counters and critical metrics in a single database aggregation pass.
        """
        base_qs = cls.get_review_queue_queryset(company=company)
        
        aggregations = base_qs.aggregate(
            total_pending=Count("id", filter=Q(computed_review_status=HRReviewStatus.PENDING)),
            critical_priority=Count("id", filter=Q(computed_priority=HRReviewPriority.CRITICAL)),
            high_priority=Count("id", filter=Q(computed_priority=HRReviewPriority.HIGH)),
            auto_closed_count=Count("id", filter=Q(computed_anomaly_type=HRAnomalyType.AUTO_CLOSED)),
            missing_checkout_count=Count("id", filter=Q(computed_anomaly_type=HRAnomalyType.MISSING_CHECKOUT)),
            resolved_today=Count("id", filter=Q(computed_review_status=HRReviewStatus.RESOLVED, updated_at__date=timezone.now().date()))
        )

        return {
            "total_pending_review": aggregations["total_pending"] or 0,
            "high_priority_alerts": (aggregations["critical_priority"] or 0) + (aggregations["high_priority"] or 0),
            "auto_closed_sheets": aggregations["auto_closed_count"] or 0,
            "missing_checkouts": aggregations["missing_checkout_count"] or 0,
            "resolved_today_count": aggregations["resolved_today"] or 0,
        }