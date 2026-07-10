# apps/attendance/api/v1/views/hr_live_workforce_views.py

from django.utils import timezone
from rest_framework import status

from apps.attendance.services.hr_live_workforce_service import HRLiveWorkforceService
from apps.attendance.api.v1.serializers.hr_live_workforce_serializers import (
    LiveWorkforceRowSerializer,
)

from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse
from apps.core.standers_pagination import (
    StandardLimitOffsetPagination,
    PaginationAdapter,
)


class HRLiveWorkforceAPIView(BaseCompanyAPIView):
    """
    Live Workforce operational endpoint.
    Replaces the legacy Employee Directory with real-time attendance state.
    """

    required_permissions = {
        "GET": "tenant.attendance.manage",
    }

    def get(self, request, *args, **kwargs):
        query_params = request.query_params.dict()

        if "date" not in query_params or not query_params["date"]:
            query_params["date"] = str(timezone.now().date())

        queryset, summary, filter_metadata = HRLiveWorkforceService.compile_live_workforce_dataset(
            company=request.company,
            params=query_params,
        )

        paginator = StandardLimitOffsetPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request, view=self)

        row_serializer = LiveWorkforceRowSerializer(paginated_queryset, many=True)
        pagination_meta = PaginationAdapter.get_metadata(paginator, paginated_queryset)

        response_data = {
            "summary": summary,
            "filter_metadata": filter_metadata,
            "results": row_serializer.data,
            "pagination": pagination_meta,
        }

        return ApiResponse.success(
            data=response_data,
            message="Live workforce data compiled successfully.",
            status=status.HTTP_200_OK,
        )