# apps/attendance/api/v1/views/verification_views.py

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse
from apps.attendance.api.v1.serializers.verification_serializers import (
    GPSVerifyRequestSerializer,
    GPSVerifyResponseSerializer,
    FaceVerifyRequestSerializer,
    FaceVerifyResponseSerializer,
)
from apps.attendance.services.method_validation_service import MethodValidationService


class GPSVerifyAPIView(BaseCompanyAPIView):
    """
    Verifies GPS location against geofence and returns a secure verification token.
    Token must be included in subsequent check-in/check-out/break request.
    """
    required_permissions = {"POST": "tenant.attendance.view"}
    
    def post(self, request: Request) -> Response:
        serializer = GPSVerifyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            result = MethodValidationService.validate_gps_and_create_token(
                company=request.company,
                membership=request.membership,
                latitude=serializer.validated_data["latitude"],
                longitude=serializer.validated_data["longitude"],
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            
            response_serializer = GPSVerifyResponseSerializer(data=result)
            response_serializer.is_valid(raise_exception=False)
            
            return ApiResponse.success(
                data=response_serializer.data,
                message="GPS location verified successfully.",
                status=status.HTTP_200_OK
            )
            
        except DjangoValidationError as exc:
            return ApiResponse.error(
                message=str(exc.message),
                status=status.HTTP_400_BAD_REQUEST
            )


class FaceVerifyAPIView(BaseCompanyAPIView):
    """
    Verifies face against enrolled profile and returns a secure verification token.
    CURRENT: Accepts browser-extracted embedding for comparison.
    FUTURE: Will accept image_base64 and process via backend AI service.
    """
    required_permissions = {"POST": "tenant.attendance.view"}
    
    def post(self, request: Request) -> Response:
        serializer = FaceVerifyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            result = MethodValidationService.validate_face_and_create_token(
                company=request.company,
                membership=request.membership,
                image_base64=serializer.validated_data.get("image_base64"),
                face_embedding=serializer.validated_data.get("face_embedding"),
                verification_method=serializer.validated_data.get(
                    "verification_method", "browser_embedding"
                ),
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )
            
            response_serializer = FaceVerifyResponseSerializer(data=result)
            response_serializer.is_valid(raise_exception=False)
            
            return ApiResponse.success(
                data=response_serializer.data,
                message="Face verified successfully.",
                status=status.HTTP_200_OK
            )
            
        except DjangoValidationError as exc:
            return ApiResponse.error(
                message=str(exc.message),
                status=status.HTTP_400_BAD_REQUEST
            )