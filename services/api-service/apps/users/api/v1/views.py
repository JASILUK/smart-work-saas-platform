from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.middleware.csrf import get_token


from apps.core.api_response import ApiResponse
from apps.core.exceptions import ApplicationError
from apps.users.selectors import get_mfa_device, get_user_mfa_devices
from apps.users.services.auth_service import AuthService
from apps.users.services.auth_strategies import MobileStrategy, WebStrategy
from apps.users.services.MFA_service import (
    BackupCodeService,
    MFALoginVerifyService,
    MFASetupService,
    MFAVerifyService,
    TempTokenService,
)
from apps.users.services.password_service import PasswordService
from apps.users.services.register_with_company import RegisterUserWithCompanyService
from apps.users.services.registration import UserRegistrationService
from apps.users.services.session_service import SessionService

from .serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    MFADeviceListSerializer,
    MFASetupSerializer,
    MFAVerifySerializer,
    RegisterInputSerializer,
    RegisterWithCompanySerializer,
    ResendVerificationSerializer,
    ResetPasswordSerializer,
    StandardLoginSerializer,
    VerifyEmailSerializer,
)


class RegisterUserAPI(APIView):
    permission_classes = []

    def post(self, request):
        serializer = RegisterInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = UserRegistrationService()
        user = service.register_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            username=serializer.validated_data["username"],
        )

        return Response(
            {
                "success": True,
                "message": "Registration successful. Please check your email for the verification code.",
                "data": {"email": user.email},
            },
            status=status.HTTP_201_CREATED,
        )


class RegisterWithCompanyAPI(APIView):

    permission_classes = []

    def post(self, request):

        serializer = RegisterWithCompanySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = RegisterUserWithCompanyService()

        user = service.execute(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            username=serializer.validated_data["username"],
            company_name=serializer.validated_data["company_name"],
        )

        return Response(
            {
                "success": True,
                "message": "Verification code sent to email.",
                "data": {"email": user.email},
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailAPI(APIView):
    """
    POST /api/v1/users/verify-email/
    """

    permission_classes = []

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client_type = request.headers.get("X-Client-Type", "web")

        email = serializer.validated_data["email"]
        token = serializer.validated_data["token"]

        service = UserRegistrationService()

        payload = service.complete_registration(email=email, token=token)
        strategy = WebStrategy() if client_type == "web" else MobileStrategy()
        return strategy.build_response(payload=payload)


class ResendVerificationAPI(APIView):
    permission_classes = []

    """
    POST /api/v1/users/resend-verification/
    """

    def post(self, request):
        serializer = ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = UserRegistrationService()

        service.resend_verification_email(email=serializer.validated_data["email"])

        return Response(
            {
                "success": True,
                "message": "A new verification code has been sent to your email.",
            },
            status=status.HTTP_200_OK,
        )


class StandardLoginAPI(APIView):
    permission_classes = []

    def post(self, request):
        serializer = StandardLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client_type = request.headers.get("X-Client-Type", "web")

        service = AuthService()
        payload = service.login_with_password(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        if payload.get("mfa_required"):
            return Response(payload, status=200)

        strategy = WebStrategy() if client_type == "web" else MobileStrategy()
        return strategy.build_response(payload=payload)


class LogoutAPI(APIView):
    """
    POST /api/v1/users/logout/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):

        refresh_token = request.COOKIES.get("refresh_token") or request.data.get(
            "refresh_token"
        )

        # 2. Grab the client type
        client_type = request.headers.get("X-Client-Type", "web")

        # 3. Execute!
        service = AuthService()
        return service.logout(refresh_token=refresh_token, client_type=client_type)


class RefreshTokenAPI(APIView):
    """
    POST /api/v1/users/refresh/
    """

    permission_classes = []

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token") or request.data.get(
            "refresh_token"
        )

        client_type = request.headers.get("X-Client-Type", "web")

        service = AuthService()
        payload = service.refresh_session(
            raw_refresh_token=refresh_token, client_type=client_type
        )
        strategy = WebStrategy() if client_type == "web" else MobileStrategy()
        return strategy.build_response(payload=payload)


class MeAPI(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        service = SessionService()

        data = service.get_user_session(request.user)

        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)


class ForgotPasswordAPI(APIView):
    permission_classes = []

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = PasswordService()
        service.request_reset(serializer.validated_data["email"])

        return Response(
            {
                "success": True,
                "message": "If this email exists, a reset link/code has been sent.",
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordAPI(APIView):
    permission_classes = []

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = PasswordService()

        service.reset_password(
            email=serializer.validated_data["email"],
            token=serializer.validated_data["token"],
            new_password=serializer.validated_data["new_password"],
        )

        return Response(
            {"success": True, "message": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )


class ChangePasswordAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = PasswordService()

        service.change_password(
            user=request.user,
            current_password=serializer.validated_data["current_password"],
            new_password=serializer.validated_data["new_password"],
        )

        return Response({"success": True, "message": "Password changed successfully."})


class MFALoginVerifyAPI(APIView):

    permission_classes = []

    def post(self, request):

        code = request.data.get("code")
        device_id = request.data.get("device_id")
        temp_token = request.data.get("temp_token")

        user = TempTokenService.decode_and_user(temp_token)

        MFALoginVerifyService(user=user, device_id=device_id, code=code).verify()

        payload = AuthService().login_after_verification(user)

        client_type = request.headers.get("X-Client-Type", "web")

        strategy = WebStrategy() if client_type == "web" else MobileStrategy()

        return strategy.build_response(payload=payload)


class MFASetupAPI(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = MFASetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = MFASetupService(request.user)

        result = service.execute(device_name=serializer.validated_data["device_name"])

        return ApiResponse.success(
            message="Scan QR with authenticator app", data=result
        )


class MFAVerifyAPI(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = MFAVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = MFAVerifyService(
            user=request.user,
            device_id=serializer.validated_data["device_id"],
            code=serializer.validated_data["code"],
        )

        backup_codes = service.verify()

        return ApiResponse.success(
            message="MFA enabled", data={"backup_codes": backup_codes}
        )


class MFADeviceListAPI(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        devices = get_user_mfa_devices(request.user)

        serializer = MFADeviceListSerializer(devices, many=True)

        return ApiResponse.success(data=serializer.data)


class MFADeviceDeleteAPI(APIView):

    permission_classes = [IsAuthenticated]

    def delete(self, request, device_id):

        device = get_mfa_device(request.user, device_id)

        if not device:
            raise ApplicationError("Device not found")

        device.delete()

        return ApiResponse.success(message="Device removed")


class MFABackupRegenerateAPI(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        service = BackupCodeService(user=request.user)

        codes = service.regenerate_codes()

        return ApiResponse.success(
            message="Backup codes regenerated", data={"backup_codes": codes}
        )


class GoogleLoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):

        id_token = request.data.get("id_token")
        client_type = request.headers.get("X-Client-Type", "web")

        if not id_token:
            return Response({"error": "Token required"}, status=400)

        service = AuthService()

        payload = service.login_with_google(id_token)

        if payload.get("mfa_required"):
            return Response(payload, status=200)

        strategy = WebStrategy() if client_type == "web" else MobileStrategy()
        return strategy.build_response(payload=payload)





class CSRFTokenView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "csrfToken": get_token(request)
        })

# class PhoneLoginAPI(APIView):
#     permission_classes = []
#     def post(self, request):
#         # ... validate phone and otp format ...
#         service = AuthService()
#         return service.login_with_phone(
#             phone=serializer.validated_data['phone'],
#             otp_code=serializer.validated_data['otp_code'],
#             client_type=request.headers.get("X-Client-Type", "web")
#         )

# class GoogleLoginAPI(APIView):
#     permission_classes = []
#     def post(self, request):
#         # ... validate google_token format ...
#         service = AuthService()
#         return service.login_with_google(
#             google_id_token=serializer.validated_data['google_token'],
#             client_type=request.headers.get("X-Client-Type", "web")
#         )
