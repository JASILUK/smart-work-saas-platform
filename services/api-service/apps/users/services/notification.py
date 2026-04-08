# integrations/services.py
from django.conf import settings

from integrations.notifications import (
    ConsoleEmailProvider,
    ConsoleSMSProvider,
    SendGridProvider,
    SMTPEmailProvider,
    TwilioSMSProvider,
)
from integrations.template_service import TemplateService


class NotificationService:
    def __init__(self):
        # Dynamically load the correct providers based on the .env file
        self.template_service = TemplateService()
        self.providers = {
            "EMAIL": self._get_email_provider(),
            "SMS": self._get_sms_provider(),
            # 'WHATSAPP': WhatsAppProvider() # You can add this easily later!
        }

    def _get_email_provider(self):
        # .lower() ensures "SENDGRID", "SendGrid", and "sendgrid" all work
        provider_name = getattr(settings, "EMAIL_PROVIDER", "console").lower()

        if provider_name == "sendgrid":
            return SendGridProvider()
        if provider_name == "smtp":
            return SMTPEmailProvider()

        # The ultimate safety net: fallback to console
        return ConsoleEmailProvider()

    def _get_sms_provider(self):
        provider_name = getattr(settings, "SMS_PROVIDER", "console").lower()

        if provider_name == "twilio":
            return TwilioSMSProvider()

        # Fallback to console so local development doesn't crash
        return ConsoleSMSProvider()

    def send_notification(
        self,
        *,
        channel: str,
        recipient: str,
        template_name: str = None,
        context: dict = None,
        content: str = None,
        subject: str = None,
    ):
        safe_channel = channel.upper()

        provider = self.providers.get(safe_channel)
        if not provider:
            raise ValueError(f"No provider configured for channel: {safe_channel}")

        # Delegate rendering decision to provider
        content = self._build_content(
            channel=safe_channel,
            template_name=template_name,
            context=context,
            content=content,
        )

        provider.send(
            recipient=recipient,
            content=content,
            subject=subject,
        )

    def _build_content(self, *, channel, template_name, context, content):

        if content:
            return content

        if not template_name:
            raise ValueError("Must provide template_name or content")

        if channel == "EMAIL":
            return self.template_service.render_email(template_name, context or {})

        if channel == "SMS":
            return self.template_service.render_sms(template_name, context or {})

        raise ValueError(f"No template handler for channel: {channel}")
