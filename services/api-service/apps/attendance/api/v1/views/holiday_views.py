from apps.core.standers_pagination import StandardLimitOffsetPagination
from rest_framework.request import Request
from django.utils.timezone import localdate

from apps.attendance.selectors import holiday_selector
from apps.attendance.services.holiday_service import HolidayService
from apps.attendance.services.holiday_import_service import HolidayImportService
from apps.attendance.api.v1.serializers.holiday_serializers import (
    HolidayCreateSerializer,
    HolidayUpdateSerializer,
    HolidayDetailSerializer,
    HolidayListSerializer,
    HolidayImportRequestSerializer,
    HolidayPreviewRequestSerializer,
    HolidayImportSummarySerializer,
)
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse




class HolidayListCreateAPI(BaseCompanyAPIView):
    required_permissions = {
        "GET": "tenant.attendance.view",
        "POST": "tenant.attendance.manage",
    }

    def get(self, request: Request):
        # 1. Fetch the base query from the selector
        base_queryset = holiday_selector.get_company_holidays(company=request.company)

        # 2. Apply query parameter filtering
        holiday_type = request.query_params.get("holiday_type")
        year = request.query_params.get("year", localdate().year)
        month = request.query_params.get("month")
        upcoming = request.query_params.get("upcoming")

        if holiday_type:
            base_queryset = base_queryset.filter(holiday_type=holiday_type)
        if year:
            base_queryset = base_queryset.filter(holiday_date__year=year)
        if month:
            base_queryset = base_queryset.filter(holiday_date__month=month)
        if upcoming and str(upcoming).lower() == "true":
            base_queryset = base_queryset.filter(holiday_date__gte=localdate())

        # 3. Call the selector to calculate the metrics before slicing for pagination
        metrics = holiday_selector.get_holiday_metrics(base_queryset)

        # 4. Paginate the dataset
        paginator = StandardLimitOffsetPagination()
        paginated_queryset = paginator.paginate_queryset(base_queryset, request, view=self)

        serializer = HolidayListSerializer(paginated_queryset, many=True)

        return ApiResponse.success(
            data={
                "meta": {
                    "count": paginator.page.paginator.count,
                    "next": paginator.get_next_link(),
                    "previous": paginator.get_previous_link(),
                    "metrics": metrics, # Clean dictionary containing total, paid, half_day, upcoming
                },
                "results": serializer.data,
            }
        )



    # =====================================================
    # CREATE HOLIDAY
    # =====================================================

    def post(self, request: Request):
        serializer = HolidayCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        holiday = HolidayService.create_holiday(
            company=request.company,
            actor=request.membership,
            validated_data=serializer.validated_data,
        )

        # Refresh from database via selector to ensure clean detail structure representation
        holiday = holiday_selector.get_company_holiday(
            company=request.company, 
            holiday_id=holiday.id
        )

        response_serializer = HolidayDetailSerializer(holiday)
        return ApiResponse.success(
            data=response_serializer.data,
            message="Holiday created.",
            status=201,
        )


class HolidayDetailAPI(BaseCompanyAPIView):

    required_permissions = {
            "GET": "tenant.attendance.view",
            "PATCH": "tenant.attendance.manage",
            "DELETE" : "tenant.attendance.manage"
        }
       

    # =====================================================
    # GET HOLIDAY DETAIL
    # =====================================================

    def get(self, request: Request, holiday_id: int):
        holiday = holiday_selector.get_company_holiday(
            company=request.company, 
            holiday_id=holiday_id
        )

        if not holiday:
            return ApiResponse.error(
                "Holiday not found.",
                status=404,
            )

        serializer = HolidayDetailSerializer(holiday)
        return ApiResponse.success(data=serializer.data)

    # =====================================================
    # UPDATE HOLIDAY
    # =====================================================

    def patch(self, request: Request, holiday_id: int):
        holiday = holiday_selector.get_company_holiday(
            company=request.company, 
            holiday_id=holiday_id
        )

        if not holiday:
            return ApiResponse.error(
                "Holiday not found.",
                status=404,
            )

        serializer = HolidayUpdateSerializer(
            holiday, 
            data=request.data, 
            partial=True
        )
        serializer.is_valid(raise_exception=True)

        holiday = HolidayService.update_holiday(
            holiday=holiday,
            actor=request.membership,
            validated_data=serializer.validated_data,
        )

        # Re-fetch from selector for output format validation matching architecture
        holiday = holiday_selector.get_company_holiday(
            company=request.company, 
            holiday_id=holiday.id
        )

        response_serializer = HolidayDetailSerializer(holiday)
        return ApiResponse.success(
            data=response_serializer.data,
            message="Holiday updated.",
        )

    # =====================================================
    # DELETE HOLIDAY
    # =====================================================

    def delete(self, request: Request, holiday_id: int):
        holiday = holiday_selector.get_company_holiday(
            company=request.company, 
            holiday_id=holiday_id
        )

        if not holiday:
            return ApiResponse.error(
                "Holiday not found.",
                status=404,
            )

        HolidayService.delete_holiday(
            holiday=holiday,
            actor=request.membership,
        )

        return ApiResponse.success(message="Holiday deleted.")






# apps/attendance/api/v1/views/holiday_views.py

class HolidayImportAPI(BaseCompanyAPIView):

    required_permissions = {
        "POST": "tenant.attendance.manage",
    }

    def post(self, request: Request):
        # 1. Parse client parameters safely
        request_serializer = HolidayImportRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        validated_data = request_serializer.validated_data

        # 2. Fire the underlying operational service
        summary_data = HolidayImportService.import_holidays(
            company=request.company,
            country_code=validated_data["country_code"],
            year=validated_data["year"],
            subdivision_code=validated_data.get("subdivision_code"),
            overwrite_existing=validated_data.get("overwrite_existing", False),
        )

        # 3. FIXED: Pass data to the serializer as an instance object block!
        # Do NOT pass it to 'data=' and do NOT call response_serializer.is_valid()
        response_serializer = HolidayImportSummarySerializer(summary_data)

        # 4. Return clean, serialized output
        return ApiResponse.success(
            data=response_serializer.data,
            message="Holidays imported successfully.",
        )


class HolidayPreviewAPI(
    BaseCompanyAPIView,
):
    """
    Provides a read-only preview of holidays
    returned by external providers before
    importing them into the database.
    """

    required_permissions = {
        "POST": "tenant.attendance.manage",
    }

    # =====================================================
    # POST - PREVIEW HOLIDAYS
    # =====================================================

    def post(
        self,
        request: Request,
    ):

        serializer = (
            HolidayPreviewRequestSerializer(
                data=request.data,
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        validated_data = (
            serializer.validated_data
        )

        preview_data = (
            HolidayImportService.preview_holidays(
                country_code=validated_data[
                    "country_code"
                ],
                year=validated_data[
                    "year"
                ],
                subdivision_code=validated_data.get(
                    "subdivision_code",
                ),
            )
        )

        return ApiResponse.success(
            data=preview_data,
        )