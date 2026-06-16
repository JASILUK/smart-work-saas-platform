from rest_framework import serializers
from rest_framework.request import Request

from apps.attendance.selectors.company_work_schedule_selector import (
    CompanyWorkScheduleSelector,
)
from apps.attendance.api.v1.serializers.company_work_schedule_serializer import (
    CompanyWorkScheduleCreateSerializer,
    CompanyWorkScheduleDetailSerializer,
    CompanyWorkScheduleUpdateSerializer,
)
from apps.attendance.services.company_work_schedule_service import (
    CompanyWorkScheduleService,
)
from apps.companies.api.base import (
    BaseCompanyAPIView,
)
from apps.core.api_response import (
    ApiResponse,
)


class ScheduleActivationSerializer(
    serializers.Serializer,
):

    is_active = serializers.BooleanField()


class CompanyWorkScheduleAPI(
    BaseCompanyAPIView,
):

    required_permissions = {
        "GET": "tenant.attendance.view",
        "POST": "tenant.attendance.manage",
    }

    # =====================================================
    # GET COMPANY SCHEDULE
    # =====================================================

    def get(
        self,
        request: Request,
    ):

        schedule = (

            CompanyWorkScheduleSelector

            .get_queryset()

            .filter(
                company=request.company,
            )

            .first()
        )

        if not schedule:

            return ApiResponse.error(
                "Company work schedule not found.",
                status=404,
            )

        serializer = (
            CompanyWorkScheduleDetailSerializer(
                schedule,
            )
        )

        return ApiResponse.success(
            data=serializer.data,
        )

    # =====================================================
    # CREATE COMPANY SCHEDULE
    # =====================================================

    def post(
        self,
        request: Request,
    ):

        serializer = (
            CompanyWorkScheduleCreateSerializer(
                data=request.data,
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        schedule = (
            CompanyWorkScheduleService.create_schedule(
                company=request.company,
                actor=request.membership,
                validated_data=serializer.validated_data,
            )
        )

        schedule = (
            CompanyWorkScheduleSelector.get_by_id(
                schedule_id=schedule.id,
            )
        )

        response_serializer = (
            CompanyWorkScheduleDetailSerializer(
                schedule,
            )
        )

        return ApiResponse.success(
            data=response_serializer.data,
            message="Company work schedule created.",
        )


class CompanyWorkScheduleDetailAPI(
    BaseCompanyAPIView,
):

    required_permissions = {
        "PATCH": "tenant.attendance.manage",
    }

    # =====================================================
    # UPDATE COMPANY SCHEDULE
    # =====================================================

    def patch(
        self,
        request: Request,
    ):

        schedule = (

            CompanyWorkScheduleSelector

            .get_queryset()

            .filter(
                company=request.company,
            )

            .first()
        )

        if not schedule:

            return ApiResponse.error(
                "Company work schedule not found.",
                status=404,
            )

        serializer = (
            CompanyWorkScheduleUpdateSerializer(
                schedule,
                data=request.data,
                partial=True,
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        schedule = (
            CompanyWorkScheduleService.update_schedule(
                schedule=schedule,
                actor=request.membership,
                validated_data=serializer.validated_data,
            )
        )

        schedule = (
            CompanyWorkScheduleSelector.get_by_id(
                schedule_id=schedule.id,
            )
        )

        response_serializer = (
            CompanyWorkScheduleDetailSerializer(
                schedule,
            )
        )

        return ApiResponse.success(
            data=response_serializer.data,
            message="Company work schedule updated.",
        )


class CompanyWorkScheduleActivationAPI(
    BaseCompanyAPIView,
):

    required_permissions = {
        "POST": "tenant.attendance.manage",
    }

    # =====================================================
    # TOGGLE SCHEDULE ACTIVATION
    # =====================================================

    def post(
        self,
        request: Request,
    ):

        schedule = (

            CompanyWorkScheduleSelector

            .get_queryset()

            .filter(
                company=request.company,
            )

            .first()
        )

        if not schedule:

            return ApiResponse.error(
                "Company work schedule not found.",
                status=404,
            )

        serializer = (
            ScheduleActivationSerializer(
                data=request.data,
            )
        )

        serializer.is_valid(
            raise_exception=True,
        )

        is_active = serializer.validated_data[
            "is_active"
        ]

        if is_active:

            schedule = (
                CompanyWorkScheduleService.activate_schedule(
                    schedule=schedule,
                    actor=request.membership,
                )
            )

            message = "Schedule activated."

        else:

            schedule = (
                CompanyWorkScheduleService.deactivate_schedule(
                    schedule=schedule,
                    actor=request.membership,
                )
            )

            message = "Schedule deactivated."

        schedule = (
            CompanyWorkScheduleSelector.get_by_id(
                schedule_id=schedule.id,
            )
        )

        response_serializer = (
            CompanyWorkScheduleDetailSerializer(
                schedule,
            )
        )

        return ApiResponse.success(
            data=response_serializer.data,
            message=message,
        )
