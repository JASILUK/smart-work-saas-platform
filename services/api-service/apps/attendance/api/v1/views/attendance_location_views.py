from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.core.api_response import ApiResponse
from apps.companies.api.base import BaseCompanyAPIView

from apps.attendance.selectors.attendance_location_selector import AttendanceLocationSelector
from apps.attendance.services.attendance_location_service import AttendanceLocationService
from apps.attendance.api.v1.serializers.attendance_location_serializers import (
    AttendanceLocationListSerializer,
    AttendanceLocationDetailSerializer,
    AttendanceLocationCreateSerializer,
    AttendanceLocationUpdateSerializer,
)


class AttendanceLocationListCreateAPI(BaseCompanyAPIView):
    """ Provides collection listings and allocation initialization entries for GPS Geofences. """
    
    required_permissions = {
        "GET": "tenant.attendance.view",
        "POST": "tenant.attendance.manage",
    }

    def get(self, request: Request) -> Response:
        company = request.company
        search_query = request.query_params.get("search", None)
        
        # Parse active_only custom filter flags smoothly out of raw queries
        active_param = request.query_params.get("active_only", None)
        active_only = None
        if active_param is not None:
            active_only = active_param.lower() in ["true", "1"]

        records = AttendanceLocationSelector.list_company_locations(
            company=company,
            active_only=active_only,
            search=search_query
        )
        
        serializer = AttendanceLocationListSerializer(records, many=True)
        return ApiResponse.success(data=serializer.data)

    def post(self, request: Request) -> Response:
        company = request.company
        actor = request.membership

        serializer = AttendanceLocationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            new_location = AttendanceLocationService.create_location(
                company=company,
                actor=actor,
                validated_data=serializer.validated_data
            )
            response_serializer = AttendanceLocationDetailSerializer(new_location)
            return ApiResponse.success(
                data=response_serializer.data,
                message="Attendance location created successfully.",
                status=status.HTTP_201_CREATED
            )
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message, status=status.HTTP_400_BAD_REQUEST)


class AttendanceLocationDetailAPI(BaseCompanyAPIView):
    """ Tracks singular mutations, detail retrievals, and administrative soft deletions. """

    required_permissions = {
        "GET": "tenant.attendance.view",
        "PATCH": "tenant.attendance.manage",
        "DELETE": "tenant.attendance.manage",
    }

    def get(self, request: Request, location_id: int) -> Response:
        company = request.company
        location = AttendanceLocationSelector.get_by_id(location_id=location_id, company=company)
        
        if not location:
            return ApiResponse.error(message="Attendance location not found.", status=status.HTTP_404_NOT_FOUND)

        serializer = AttendanceLocationDetailSerializer(location)
        return ApiResponse.success(data=serializer.data)

    def patch(self, request: Request, location_id: int) -> Response:
        company = request.company
        location = AttendanceLocationSelector.get_by_id(location_id=location_id, company=company)
        
        if not location:
            return ApiResponse.error(message="Attendance location not found.", status=status.HTTP_404_NOT_FOUND)

        serializer = AttendanceLocationUpdateSerializer(location, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            updated_location = AttendanceLocationService.update_location(
                location=location,
                validated_data=serializer.validated_data
            )
            response_serializer = AttendanceLocationDetailSerializer(updated_location)
            return ApiResponse.success(
                data=response_serializer.data,
                message="Attendance location updated successfully."
            )
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request: Request, location_id: int) -> Response:
        company = request.company
        location = AttendanceLocationSelector.get_by_id(location_id=location_id, company=company)
        
        if not location:
            return ApiResponse.error(message="Attendance location not found.", status=status.HTTP_404_NOT_FOUND)

        # Confirm deactivation doesn't isolate system context from all tracking options
        active_count = AttendanceLocationSelector.list_company_locations(company=company, active_only=True).count()
        if location.is_active and active_count <= 1:
            return ApiResponse.error(
                message="Cannot deactivate the last active geofence perimeter. Provide a replacement first.",
                status=status.HTTP_400_BAD_REQUEST
            )

        AttendanceLocationService.deactivate_location(location=location)
        return ApiResponse.success(message="Attendance location deactivated successfully.")


class ActivateAttendanceLocationAPI(BaseCompanyAPIView):
    """ Targets restoration routines to safely reactivate single geofences. """
    
    required_permissions = {
        "POST": "tenant.attendance.manage",
    }

    def post(self, request: Request, location_id: int) -> Response:
        company = request.company
        location = AttendanceLocationSelector.get_by_id(location_id=location_id, company=company)
        
        if not location:
            return ApiResponse.error(message="Attendance location not found.", status=status.HTTP_404_NOT_FOUND)

        try:
            AttendanceLocationService.activate_location(location=location)
            return ApiResponse.success(message="Attendance location activated successfully.")
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message, status=status.HTTP_400_BAD_REQUEST)