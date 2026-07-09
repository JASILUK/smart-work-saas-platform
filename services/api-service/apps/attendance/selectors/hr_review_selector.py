# apps/attendance/selectors/hr_review_selector.py
import datetime
from django.db.models import QuerySet, Q, Count
from django.utils import timezone
from apps.companies.models import Company
from apps.attendance.models.daily_attendance import DailyAttendance, DailyAttendanceStatus

class HRReviewSelector:
    """
    High-performance selector isolating anomalies from the DailyAttendance summary ledger.
    Optimizes memory footprints and network queries using selective prefetching and indexes.
    """

    @classmethod
    def get_dashboard_metrics(cls, *, company: Company) -> dict:
        """
        Executes an atomic database-level aggregation to fetch analytical metrics 
        for the review queue overview sheet in a single query execution path.
        """
        today = timezone.now().date()
        
        metrics = DailyAttendance.objects.filter(
            company=company,
            needs_review=True
        ).aggregate(
            review_count=Count("id"),
            auto_closed_count=Count("id", filter=Q(is_auto_closed=True)),
            missing_checkout_count=Count(
                "id", 
                filter=Q(
                    first_check_in_at__isnull=False, 
                    last_check_out_at__isnull=True, 
                    is_auto_closed=False
                )
            ),
            # Duplicate punches frequently trigger specific log trace indicators in review_reason strings
            duplicate_punches_count=Count(
                "id", 
                filter=Q(review_reason__icontains="duplicate") | Q(review_reason__icontains="double")
            ),
            unresolved_count=Count("id", filter=Q(finalized_at__isnull=True)),
            today_review_count=Count("id", filter=Q(attendance_date=today))
        )

        return {
            "review_count": metrics["review_count"] or 0,
            "auto_closed_count": metrics["auto_closed_count"] or 0,
            "missing_checkout_count": metrics["missing_checkout_count"] or 0,
            "duplicate_punches_count": metrics["duplicate_punches_count"] or 0,
            "unresolved_count": metrics["unresolved_count"] or 0,
            "today_review_count": metrics["today_review_count"] or 0,
        }

    @classmethod
    def list_review_records(cls, *, company: Company, filters: dict) -> QuerySet[DailyAttendance]:
        """
        Builds a single-pass optimized dataset query mapping filters down indexed database boundaries.
        """
        queryset = DailyAttendance.objects.select_related(
            "membership",
            "membership__user",
            "membership__department"
        ).filter(
            company=company,
            needs_review=True
        )

        # Apply standard parameters filters
        if filters.get("date"):
            queryset = queryset.filter(attendance_date=filters["date"])
        if filters.get("date_from") and filters.get("date_to"):
            queryset = queryset.filter(attendance_date__range=(filters["date_from"], filters["date_to"]))
        if filters.get("department"):
            queryset = queryset.filter(membership__department_id=filters["department"])
        if filters.get("employee"):
            queryset = queryset.filter(membership_id=filters["employee"])
        if filters.get("status"):
            queryset = queryset.filter(attendance_status=filters["status"])
        if filters.get("review_reason"):
            queryset = queryset.filter(review_reason__icontains=filters["review_reason"])
            
        if filters.get("search"):
            search_query = filters["search"]
            queryset = queryset.filter(
                Q(membership__user__first_name__icontains=search_query) |
                Q(membership__user__last_name__icontains=search_query) |
                Q(membership__user__email__icontains=search_query) |
                Q(review_reason__icontains=search_query)
            )

        ordering = filters.get("ordering", "-attendance_date")
        return queryset.order_by(ordering)

    @classmethod
    def get_review_record(cls, *, company: Company, record_id: int) -> DailyAttendance:
        """
        Retrieves a locked row with full related context parameters inside an evaluation window block.
        """
        return DailyAttendance.objects.select_related(
            "membership",
            "membership__user"
        ).filter(
            id=record_id, 
            company=company
        ).first()