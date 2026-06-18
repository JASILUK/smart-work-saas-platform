from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.core.api_response import ApiResponse
from apps.companies.api.base import BaseCompanyAPIView

from apps.attendance.selectors.biometric_device_selector import BiometricDeviceSelector
from apps.attendance.selectors.biometric_employee_mapping_selector import BiometricEmployeeMappingSelector
from apps.attendance.services.biometric_device_service import BiometricDeviceService
from apps.attendance.services.biometric_employee_mapping_service import BiometricEmployeeMappingService

from apps.attendance.api.v1.serializers.biometric_device_serializer import (
    BiometricDeviceListSerializer, BiometricDeviceDetailSerializer, 
    BiometricDeviceCreateSerializer, BiometricDeviceUpdateSerializer
)
from apps.attendance.api.v1.serializers.biometric_employee_mapping_serializer import (
    BiometricEmployeeMappingListSerializer, BiometricEmployeeMappingDetailSerializer,
    BiometricEmployeeMappingCreateSerializer, BiometricEmployeeMappingUpdateSerializer
)



# ─────────────────────────────────────────────────────────────────────────────
# Region: Biometric Devices Endpoint Views
# ─────────────────────────────────────────────────────────────────────────────

class BiometricDeviceListCreateAPI(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view", "POST": "tenant.attendance.manage"}

    def get(self, request: Request) -> Response:
        company = request.company
        records = BiometricDeviceSelector.get_company_devices(company=company)

        if "brand" in request.query_params:
            records = records.filter(brand=request.query_params["brand"])
        if "sync_mode" in request.query_params:
            records = records.filter(sync_mode=request.query_params["sync_mode"])
        if "active_only" in request.query_params:
            is_active = request.query_params["active_only"].lower() in ["true", "1"]
            records = records.filter(is_active=is_active)

        serializer = BiometricDeviceListSerializer(records, many=True)
        return ApiResponse.success(data=serializer.data)

    def post(self, request: Request) -> Response:
        serializer = BiometricDeviceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            device = BiometricDeviceService.create_device(company=request.company, validated_data=serializer.validated_data)
            return ApiResponse.success(data=BiometricDeviceDetailSerializer(device).data, message="Biometric terminal added successfully.", status=status.HTTP_201_CREATED)
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)


class BiometricDeviceDetailAPI(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view", "PATCH": "tenant.attendance.manage", "DELETE": "tenant.attendance.manage"}

    def get(self, request: Request, pk: int) -> Response:
        device = BiometricDeviceSelector.get_by_id(device_id=pk, company=request.company)
        if not device: return ApiResponse.error(message="Biometric device terminal configuration not found.", status=status.HTTP_404_NOT_FOUND)
        return ApiResponse.success(data=BiometricDeviceDetailSerializer(device).data)

    def patch(self, request: Request, pk: int) -> Response:
        device = BiometricDeviceSelector.get_by_id(device_id=pk, company=request.company)
        if not device: return ApiResponse.error(message="Biometric device terminal configuration not found.", status=status.HTTP_404_NOT_FOUND)
        serializer = BiometricDeviceUpdateSerializer(device, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            updated_device = BiometricDeviceService.update_device(device=device, validated_data=serializer.validated_data)
            return ApiResponse.success(data=BiometricDeviceDetailSerializer(updated_device).data, message="Biometric terminal configuration updated.")
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)

    def delete(self, request: Request, pk: int) -> Response:
        device = BiometricDeviceSelector.get_by_id(device_id=pk, company=request.company)
        if not device: return ApiResponse.error(message="Biometric device terminal configuration not found.", status=status.HTTP_404_NOT_FOUND)
        BiometricDeviceService.deactivate_device(device=device)
        return ApiResponse.success(message="Biometric device terminal configuration soft-deactivated successfully.")


class BiometricDeviceActivateAPI(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request: Request, pk: int) -> Response:
        device = BiometricDeviceSelector.get_by_id(device_id=pk, company=request.company)
        if not device: return ApiResponse.error(message="Biometric device terminal configuration not found.", status=status.HTTP_404_NOT_FOUND)
        BiometricDeviceService.activate_device(device=device)
        return ApiResponse.success(message="Biometric device terminal configuration reactivated.")


# ─────────────────────────────────────────────────────────────────────────────
# Region: Biometric Employee Mappings Endpoint Views
# ─────────────────────────────────────────────────────────────────────────────

class BiometricEmployeeMappingListCreateAPI(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view", "POST": "tenant.attendance.manage"}

    def get(self, request: Request) -> Response:
        records = BiometricEmployeeMappingSelector.get_company_mappings(company=request.company)

        if "membership_id" in request.query_params:
            records = records.filter(membership_id=request.query_params["membership_id"])
        if "device_id" in request.query_params:
            records = records.filter(device_id=request.query_params["device_id"])
        if "active_only" in request.query_params:
            is_active = request.query_params["active_only"].lower() in ["true", "1"]
            records = records.filter(is_active=is_active)

        serializer = BiometricEmployeeMappingListSerializer(records, many=True)
        return ApiResponse.success(data=serializer.data)

    def post(self, request: Request) -> Response:
        serializer = BiometricEmployeeMappingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            mapping = BiometricEmployeeMappingService.create_mapping(
                company=request.company,
                actor=request.membership,
                validated_data=serializer.validated_data
            )
            return ApiResponse.success(data=BiometricEmployeeMappingDetailSerializer(mapping).data, message="Employee biometric user mapping registered.", status=status.HTTP_201_CREATED)
        except DjangoValidationError as exc:
            return ApiResponse.error(message=exc.message)


class BiometricEmployeeMappingDetailAPI(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view", "PATCH": "tenant.attendance.manage", "DELETE": "tenant.attendance.manage"}

    def get(self, request: Request, pk: int) -> Response:
        mapping = BiometricEmployeeMappingSelector.get_by_id(mapping_id=pk, company=request.company)
        if not mapping: return ApiResponse.error(message="Biometric mapping profile record not found.", status=status.HTTP_404_NOT_FOUND)
        return ApiResponse.success(data=BiometricEmployeeMappingDetailSerializer(mapping).data)

    def patch(self, request: Request, pk: int) -> Response:
        mapping = BiometricEmployeeMappingSelector.get_by_id(mapping_id=pk, company=request.company)
        if not mapping: return ApiResponse.error(message="Biometric mapping profile record not found.", status=status.HTTP_404_NOT_FOUND)
        serializer = BiometricEmployeeMappingUpdateSerializer(mapping, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_mapping = BiometricEmployeeMappingService.update_mapping(mapping=mapping, validated_data=serializer.validated_data)
        return ApiResponse.success(data=BiometricEmployeeMappingDetailSerializer(updated_mapping).data, message="Mapping configuration patched.")

    def delete(self, request: Request, pk: int) -> Response:
        mapping = BiometricEmployeeMappingSelector.get_by_id(mapping_id=pk, company=request.company)
        if not mapping: return ApiResponse.error(message="Biometric mapping profile record not found.", status=status.HTTP_404_NOT_FOUND)
        BiometricEmployeeMappingService.deactivate_mapping(mapping=mapping)
        return ApiResponse.success(message="Mapping configuration tracking profile softly deactivated.")


class BiometricEmployeeMappingActivateAPI(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request: Request, pk: int) -> Response:
        mapping = BiometricEmployeeMappingSelector.get_by_id(mapping_id=pk, company=request.company)
        if not mapping: return ApiResponse.error(message="Biometric mapping profile record not found.", status=status.HTTP_404_NOT_FOUND)
        BiometricEmployeeMappingService.activate_mapping(mapping=mapping)
        return ApiResponse.success(message="Mapping configuration tracking connection reactivated.")