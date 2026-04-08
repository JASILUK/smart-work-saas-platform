# users/services/verification_service.py

import random
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from integrations.template_service import TemplateService
from apps.users.models import VerificationToken
from apps.users.services.notification import NotificationService
from apps.users.tasks.notification_tasks import send_notification_task


class VerificationService:
    # Map the Enum choices to expiry minutes
    EXPIRY_MAP = {
        VerificationToken.TokenType.EMAIL_VERIFY: 15,
        VerificationToken.TokenType.PASSWORD_RESET: 20,
        VerificationToken.TokenType.TWO_FACTOR: 5,
        VerificationToken.TokenType.INVITE: 1440,
    }

    def __init__(self):
        self.notification_service = NotificationService()
        self.template_service = TemplateService()
        # Fallback to localhost if FRONTEND_URL isn't in settings
        self.frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")

    def send(
        self,
        *,
        user,
        token_type,  # VerificationToken.TokenType choice
        mode,  # "OTP" or "LINK"
        channel="EMAIL",  # "EMAIL" or "SMS"
    ):
        # 1️⃣ Validate TokenType
        if token_type not in VerificationToken.TokenType.values:
            raise ValueError(f"Invalid token type: {token_type}")

        expiry_minutes = self.EXPIRY_MAP.get(token_type, 15)

        # 2️⃣ Generate raw token
        if mode == "OTP":
            raw_token = str(random.randint(100000, 999999))
        elif mode == "LINK":
            raw_token = secrets.token_urlsafe(32)
        else:
            raise ValueError("Invalid mode: Choose 'OTP' or 'LINK'")

        # 3️⃣ Deactivate existing unused tokens for this user/type
        VerificationToken.objects.filter(
            user=user, token_type=token_type, is_used=False
        ).update(is_used=True)

        # 4️⃣ Save hashed token to DB
        VerificationToken.objects.create(
            user=user,
            token_type=token_type,
            token=make_password(raw_token),
            expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
        )

        # 5️⃣ Build Context for templates
        context = {
            "code": raw_token if mode == "OTP" else None,
            "link": (
                f"{self.frontend_url}/reset-password?token={raw_token}&email={user.email}&type={token_type}"
                if mode == "LINK"
                else None
            ),
            "expiry_minutes": expiry_minutes,
            "user": user,
        }

        # 6️⃣ Render and Send
        template_name = token_type.lower()

        if channel == "EMAIL":
            content = self.template_service.render_email(template_name, context)
            subject = self._build_subject(token_type)
        else:  # SMS
            content = self.template_service.render_sms(template_name, context)
            subject = None  # SMS usually doesn't have a subject

        send_notification_task.delay(
            channel=channel,
            recipient=user.email if channel == "EMAIL" else user.phone_number,
            subject=subject,
            content=content,
        )
        # self.notification_service.send_notification(
        #     channel=channel,
        #     recipient=user.email if channel == "EMAIL" else user.phone_number,
        #     subject=subject,
        #     content=content,  # Consolidated into one 'content' field
        # )

    def verify(self, *, user, token_type, raw_token):
        """Finds the latest active token and validates it."""
        token_obj = (
            VerificationToken.objects.filter(
                user=user, token_type=token_type, is_used=False
            )
            .order_by("-created_at")
            .first()
        )

        if not token_obj:
            raise Exception("No active verification request found.")

        if token_obj.expires_at < timezone.now():
            raise Exception("This code has expired.")

        if not check_password(raw_token, token_obj.token):
            raise Exception("Invalid code or link.")

        # Mark as used upon successful verification
        token_obj.is_used = True
        token_obj.save()
        return True

    def _build_subject(self, token_type):
        subjects = {
            VerificationToken.TokenType.EMAIL_VERIFY: "Verify Your Email",
            VerificationToken.TokenType.PASSWORD_RESET: "Password Reset Request",
            VerificationToken.TokenType.TWO_FACTOR: "Your Login Code",
            VerificationToken.TokenType.INVITE: "Welcome to the Platform!",
        }
        return subjects.get(token_type, "Security Verification")
