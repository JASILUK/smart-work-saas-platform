from django.conf import settings

from integrations.notifications import (
SMTPEmailProvider,
SendGridProvider,
)

class EmailService:


    # =====================================================
    # PROVIDER
    # =====================================================

    @staticmethod
    def get_provider():

        provider = getattr(
            settings,
            "EMAIL_PROVIDER",
            "smtp",
        )

        if provider == "sendgrid":
            return SendGridProvider()

        return SMTPEmailProvider()

    # =====================================================
    # SEND EMAIL
    # =====================================================

    @classmethod
    def send_email(
        cls,
        *,
        recipient,
        subject,
        content,
    ):

        provider = cls.get_provider()

        return provider.send(
            recipient=recipient,
            subject=subject,
            content=content,
        )

    # =====================================================
    # MEETING EMAIL
    # =====================================================

    @classmethod
    def send_meeting_email(
        cls,
        *,
        recipient,
        title,
        body,
    ):

        return cls.send_email(
            recipient=recipient,
            subject=title,
            content=body,
        )

    # =====================================================
    # SYSTEM EMAIL
    # =====================================================

    @classmethod
    def send_system_email(
        cls,
        *,
        recipient,
        title,
        body,
    ):

        return cls.send_email(
            recipient=recipient,
            subject=title,
            content=body,
        )


    
