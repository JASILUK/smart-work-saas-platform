# users/strategies.py

from abc import ABC, abstractmethod


class BaseVerificationStrategy(ABC):

    expiry_minutes = 15
    supported_channels = ["EMAIL"]

    @abstractmethod
    def generate_token(self):
        pass

    @abstractmethod
    def build_message(self, raw_token, user, context):
        pass

    def resolve_recipient(self, user, channel):

        if channel == "EMAIL":
            return user.email

        if channel == "SMS":
            return getattr(user, "phone_number", None)

        raise ValueError("Unsupported channel")

    def get_expiry(self):
        return self.expiry_minutes

    from abc import ABC, abstractmethod


import random


class VerificationStrategyRegistry:

    _strategies = {}

    @classmethod
    def register(cls, name):
        def decorator(strategy_class):
            cls._strategies[name] = strategy_class()
            return strategy_class

        return decorator

    @classmethod
    def get(cls, name):
        strategy = cls._strategies.get(name)
        if not strategy:
            raise ValueError("Strategy not found")
        return strategy


@VerificationStrategyRegistry.register("OTP")
class OTPStrategy(BaseVerificationStrategy):

    supported_channels = ["EMAIL", "SMS"]
    expiry_minutes = 10

    def generate_token(self):
        return str(random.randint(100000, 999999))

    def build_message(self, raw_token, user, context):

        purpose = context.get("purpose", "verification")

        return {
            "subject": f"{purpose} code",
            "content": f"Your verification code is: {raw_token}",
        }


import secrets

from django.conf import settings

from apps.users.services.verification.base import BaseVerificationStrategy
from apps.users.services.verification.registry import VerificationStrategyRegistry


@VerificationStrategyRegistry.register("LINK")
class LinkStrategy(BaseVerificationStrategy):

    supported_channels = ["EMAIL"]
    expiry_minutes = 20

    def generate_token(self):
        return secrets.token_urlsafe(32)

    def build_message(self, raw_token, user, context):

        purpose = context.get("purpose")
        frontend_url = context.get("frontend_url")

        link = f"{frontend_url}?token={raw_token}&email={user.email}"

        return {"subject": f"{purpose}", "content": f"Click here: {link}"}


import random
import secrets
from abc import ABC, abstractmethod

from django.conf import settings
from django.template.loader import render_to_string


class VerificationStrategy(ABC):
    @abstractmethod
    def generate_token(self) -> str:
        """Generates the raw secret (OTP or Hash)"""
        pass

    @abstractmethod
    def get_channel(self) -> str:
        """Returns 'EMAIL' or 'SMS'"""
        pass

    @abstractmethod
    def build_message(self, token: str, user) -> dict:
        """Returns subject and content (HTML or Plain Text)"""
        pass


# --- STRATEGY 1: EMAIL OTP ---
class EmailOTPStrategy(VerificationStrategy):
    def generate_token(self) -> str:
        return str(random.randint(100000, 999999))

    def get_channel(self) -> str:
        return "EMAIL"

    def build_message(self, token: str, user) -> dict:
        # We inject the token into a beautiful HTML file!
        html_content = render_to_string(
            "email/otp_email.html", {"user": user, "otp_code": token}
        )
        return {"subject": "Your Security Code", "content": html_content}


# --- STRATEGY 2: MAGIC LINK ---
class MagicLinkStrategy(VerificationStrategy):
    def generate_token(self) -> str:
        return secrets.token_urlsafe(32)

    def get_channel(self) -> str:
        return "EMAIL"

    def build_message(self, token: str, user) -> dict:
        # Build the frontend URL
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        magic_link = f"{frontend_url}/verify?token={token}"

        # Inject the link into the HTML button
        html_content = render_to_string(
            "email/magic_link.html", {"user": user, "magic_link": magic_link}
        )
        return {"subject": "Sign in to your account", "content": html_content}


# --- STRATEGY 3: SMS OTP ---
class SMSOTPStrategy(VerificationStrategy):
    def generate_token(self) -> str:
        return str(random.randint(100000, 999999))

    def get_channel(self) -> str:
        return "SMS"

    def build_message(self, token: str, user) -> dict:
        # SMS does not use HTML templates, just plain text!
        return {
            "subject": None,
            "content": f"Your SaaS code is: {token}. Do not share this with anyone.",
        }
