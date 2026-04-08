# integrations/providers.py
import logging
from abc import ABC, abstractmethod

from django.conf import settings
from django.core.mail import send_mail
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client

logger = logging.getLogger(__name__)


# ==========================================
# 1. THE UNIFIED CONTRACT (Interface)
# ==========================================
class NotificationProvider(ABC):
    """
    EVERY provider must use this exact method signature.
    This is what makes the system 'pluggable'.
    """

    @abstractmethod
    def send(self, recipient: str, content: str, subject: str = None) -> bool:
        pass


# ==========================================
# 2. EMAIL IMPLEMENTATIONS
# ==========================================
class ConsoleEmailProvider(NotificationProvider):
    def send(self, recipient: str, content: str, subject: str = None) -> bool:
        print("\n" + "=" * 50)
        print(f"📧 CONSOLE EMAIL")
        print(f"To: {recipient}")
        print(f"Subject: {subject}")
        print(f"Body: {content}")
        print("=" * 50 + "\n")
        return True


class SMTPEmailProvider(NotificationProvider):
    def send(self, recipient: str, content: str, subject: str = None) -> bool:
        try:
            send_mail(
                subject=subject or "Notification",
                message="",  # Leave blank if using HTML
                from_email=getattr(
                    settings, "DEFAULT_FROM_EMAIL", "mohsjasil2004@gmail.com"
                ),
                recipient_list=[recipient],
                html_message=content,
                fail_silently=False,
            )
            return True
        except Exception as e:
            logger.exception("SMTP Email failed", exc_info=e)
            return False


class SendGridProvider(NotificationProvider):
    def send(self, recipient: str, content: str, subject: str = None) -> bool:
        message = Mail(
            from_email=getattr(
                settings, "DEFAULT_FROM_EMAIL", "mohdjasil2004@gmail.com"
            ),
            to_emails=recipient,
            subject=subject or "Notification",
            html_content=content,
        )
        try:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)
            return response.status_code in [200, 201, 202]
        except Exception as e:
            logger.exception("SendGrid API failed", exc_info=e)
            return False


# ==========================================
# 3. SMS IMPLEMENTATIONS
# ==========================================
class ConsoleSMSProvider(NotificationProvider):
    def send(self, recipient: str, content: str, subject: str = None) -> bool:
        print("\n" + "=" * 50)
        print(f"📱 CONSOLE SMS")
        print(f"To: {recipient}")
        print(f"Message: {content}")
        print("=" * 50 + "\n")
        return True


class TwilioSMSProvider(NotificationProvider):
    def send(self, recipient: str, content: str, subject: str = None) -> bool:
        try:
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            msg = client.messages.create(
                body=content, from_=settings.TWILIO_PHONE_NUMBER, to=recipient
            )
            return msg.error_code is None
        except Exception as e:
            logger.exception("Twilio API failed", exc_info=e)
            return False
