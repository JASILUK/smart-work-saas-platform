# users/services/auth.py
from django.contrib.auth.hashers import check_password
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.billing.services.subscription_service import SubscriptionService
from apps.companies.services.membership_service import MembershipService
from apps.core.exceptions import (
    ApplicationError,
    InvalidCredentialsError,
    UnverifiedAccountError,
)
from integrations.auth_engines import JWTAuthEngine
from integrations.Oauth.google import GoogleOAuthService
from apps.users.selectors import (
    get_user_by_email,
    get_user_by_id,
    get_user_mfa_devices,
    user_has_mfa_enabled,
)
from apps.users.services.MFA_service import TempTokenService
from apps.users.services.OauthService import OAuthService

from .auth_strategies import MobileStrategy, WebStrategy

# (Pretend we have a GoogleService that talks to Google's API)
# from integrations.services import GoogleAuthClient


class AuthService:
    def __init__(self):
        # We load the JWT Engine here
        self.engine = JWTAuthEngine()

    def _get_strategy(self, client_type: str):
        """The Factory: Routes traffic based on the X-Client-Type header."""
        strategies = {
            "mobile": MobileStrategy(),
            "web": WebStrategy(),
        }
        # If the frontend forgets to send the header, default to 'web' for safety
        return strategies.get(client_type.lower(), WebStrategy())

    def login_with_password(self, email: str, password: str):

        user = get_user_by_email(email)

        if not user or not check_password(password, user.password):
            raise InvalidCredentialsError(email=email)

        if not user.is_verified:
            raise UnverifiedAccountError(email=email)

        if user_has_mfa_enabled(user):

            temp_token = TempTokenService.create(user)

            devices = [
                {"id": device.id, "name": device.name}
                for device in get_user_mfa_devices(user=user)
            ]

            return {"mfa_required": True, "temp_token": temp_token, "devices": devices}

        return self._build_login_payload(user)

    def login_after_verification(self, user):
        return self._build_login_payload(user)

    def _build_login_payload(self, user):

        tokens = self.engine.issue(user)

        return {
            "tokens": tokens,
            "user": {
                "id": user.id,
                "email": user.email,
            },
        }

    def logout(self, refresh_token: str, client_type: str) -> Response:
        """
        Blacklists the refresh token and clears client data via the Strategy.
        """
        if not refresh_token:
            raise ApplicationError("No refresh token provided.", status_code=400)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            # If the token is ALREADY expired or invalid, we don't crash.
            # The goal is achieved: the token is dead.
            pass

        # 2. THE DELIVERY: Hand off to the Strategy to clear the cookies/json
        strategy = self._get_strategy(client_type)
        return strategy.issue_logout_response()

    def refresh_session(self, raw_refresh_token: str, client_type: str) -> Response:
        """
        Takes an old refresh token, blacklists it, and issues brand new tokens (Rotation).
        """
        if not raw_refresh_token:
            raise ApplicationError(
                "No refresh token provided. Please log in.", status_code=401
            )

        try:
            old_token = RefreshToken(raw_refresh_token)

            user_id = old_token.payload.get("user_id")
            user = get_user_by_id(user_id)

            if not user or not user.is_active:
                raise ApplicationError("User not found or inactive.", status_code=401)

            old_token.blacklist()

            payload = self._build_login_payload(user=user)
            return payload

        except TokenError:
            raise ApplicationError(
                "Refresh token is invalid or expired. Please log in again.",
                status_code=401,
            )

    def login_with_google(self, id_token):

        google_data = GoogleOAuthService.verify_token(id_token)

        user = OAuthService.get_or_create_user(
            provider="google",
            provider_id=google_data["provider_id"],
            email=google_data["email"],
            extra_data=google_data,
        )

        if user_has_mfa_enabled(user):

            temp_token = TempTokenService.create(user)

            devices = [
                {"id": device.id, "name": device.name}
                for device in get_user_mfa_devices(user=user)
            ]

            return {"mfa_required": True, "temp_token": temp_token, "devices": devices}

        return self._build_login_payload(user)

    # # --- METHOD 2: PHONE OTP LOGIN (Future Feature) ---
    # def login_with_phone(self, phone: str, otp_code: str, client_type: str) -> Response:
    #     """User types their phone number and the 6-digit SMS code."""

    #     # 1. Ask your existing VerificationService to check the code!
    #     # (If the code is wrong/expired, this will automatically raise your custom errors)
    #     user = self.verification_service.consume_token(
    #         identifier=phone, # You would update consume_token to accept phone or email
    #         token=otp_code,
    #         token_type='SMS_OTP'
    #     )

    #     if not user.is_verified:
    #         raise UnverifiedAccountError()

    #     # 2. Success! Hand off to the Strategy!
    #     strategy = self._get_strategy(client_type)
    #     return strategy.issue_response(user)
