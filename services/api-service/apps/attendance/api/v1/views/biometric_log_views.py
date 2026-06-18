from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.core.api_response import ApiResponse
from apps.companies.api.base import BaseCompanyAPIView
from apps.attendance.models.biometric_device import BiometricDevice

from apps.attendance.selectors.biometric_log_selector import BiometricLogSelector
from apps.attendance.services.biometric_manual_import_service import BiometricManualImportService
from apps.attendance.services.biometric_push_ingestion_service import BiometricPushIngestionService
from apps.attendance.api.v1.serializers.biometric_log_serializer import (
    BiometricLogListSerializer, BiometricLogDetailSerializer, ManualImportSerializer, PushWebhookSerializer
)


class BiometricLogListAPI(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request: Request) -> Response:
        records = BiometricLogSelector.get_company_logs(company=request.company)

        if "membership_id" in request.query_params:
            records = records.filter(membership_id=request.query_params["membership_id"])
        if "device_id" in request.query_params:
            records = records.filter(device_id=request.query_params["device_id"])
        if "processing_status" in request.query_params:
            records = records.filter(processing_status=request.query_params["processing_status"])
        if "source" in request.query_params:
            records = records.filter(source=request.query_params["source"])
        if "start_date" in request.query_params:
            records = records.filter(punch_time__gte=request.query_params["start_date"])
        if "end_date" in request.query_params:
            records = records.filter(punch_time__lte=request.query_params["end_date"])

        serializer = BiometricLogListSerializer(records, many=True)
        return ApiResponse.success(data=serializer.data)


class BiometricLogDetailAPI(BaseCompanyAPIView):
    required_permissions = {"GET": "tenant.attendance.view"}

    def get(self, request: Request, pk: int) -> Response:
        log = BiometricLogSelector.get_by_id(log_id=pk, company=request.company)
        if not log:
            return ApiResponse.error(message="Biometric transaction event instance log not found.", status=status.HTTP_404_NOT_FOUND)
        return ApiResponse.success(data=BiometricLogDetailSerializer(log).data)


class ManualImportAPI(BaseCompanyAPIView):
    required_permissions = {"POST": "tenant.attendance.manage"}

    def post(self, request: Request) -> Response:
        serializer = ManualImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        result = BiometricManualImportService.import_logs(
            company=request.company,
            rows=serializer.validated_data["logs"]
        )
        return ApiResponse.success(data=result, message="Manual punch records file integrated.")


class PushWebhookAPI(APIView):
    """
    Public API view designed to ingest real-time payloads from remote biometric devices.
    Authenticates requests via a device-specific webhook token query parameter.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request) -> Response:
        token = request.query_params.get("token")
        if not token:
            return Response({"detail": "Authentication access webhook token parameter is missing."}, status=status.HTTP_401_UNAUTHORIZED)

        device = BiometricDevice.objects.select_related("company").filter(webhook_token=token).first()
        if not device:
            return Response({"detail": "Invalid or revoked identification access token profile."}, status=status.HTTP_401_UNAUTHORIZED)

        if not device.is_active:
            return Response({"detail": "Target processing hardware terminal is currently deactivated."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PushWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = BiometricPushIngestionService.ingest_payload(
            company=device.company,
            device=device,
            payload=serializer.validated_data["punches"]
        )
        return Response(result, status=status.HTTP_200_OK)