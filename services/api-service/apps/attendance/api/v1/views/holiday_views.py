from django.utils.timezone import localdate
from rest_framework.request import Request

from apps.attendance.api.v1.serializers.holiday_serializers import (
    HolidayCreateSerializer,
    HolidayDetailSerializer,
    HolidayImportRequestSerializer,
    HolidayImportSummarySerializer,
    HolidayListSerializer,
    HolidayPreviewRequestSerializer,
    HolidayUpdateSerializer,
)
from apps.attendance.selectors.holiday_selector import HolidaySelector
from apps.attendance.services.holiday_import_service import HolidayImportService
from apps.attendance.services.holiday_service import HolidayService
from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse
from apps.core.standers_pagination import (
    StandardLimitOffsetPagination,
    PaginationAdapter,
)


class HolidayListCreateAPI(BaseCompanyAPIView):
    required_permissions = {
        "GET": "tenant.attendance.view",
        "POST": "tenant.attendance.manage",
    }

    def get(self, request: Request):
        # Base queryset
        queryset = HolidaySelector.get_company_holidays(
            company=request.company
        )

        # Filters
        holiday_type = request.query_params.get("holiday_type")
        year = request.query_params.get("year", localdate().year)
        month = request.query_params.get("month")
        upcoming = request.query_params.get("upcoming")

        if holiday_type:
            queryset = queryset.filter(holiday_type=holiday_type)

        if year:
            queryset = queryset.filter(holiday_date__year=year)

        if month:
            queryset = queryset.filter(holiday_date__month=month)

        if upcoming and str(upcoming).lower() == "true":
            queryset = queryset.filter(
                holiday_date__gte=localdate()
            )

        # Metrics before pagination
        metrics = HolidaySelector.get_holiday_metrics(queryset)

        # Pagination
        paginator = StandardLimitOffsetPagination()
        page = paginator.paginate_queryset(
            queryset,
            request,
            view=self,
        )

        serializer = HolidayListSerializer(page, many=True)

        pagination_meta = PaginationAdapter.get_metadata(
            paginator,
            page,
        )

        return ApiResponse.success(
            data={
                "meta": {
                    **pagination_meta,
                    "metrics": metrics,
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
        holiday = HolidaySelector.get_company_holiday(
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
        holiday = HolidaySelector.get_company_holiday(
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
        holiday = HolidaySelector.get_company_holiday(
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
        holiday = HolidaySelector.get_company_holiday(
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
        holiday = HolidaySelector.get_company_holiday(
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