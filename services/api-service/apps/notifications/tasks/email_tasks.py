from celery import shared_task

from apps.notifications.services.email_service import (
    EmailService,
)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_email_task(
    self,
    *,
    recipient,
    subject,
    content,
):

    try:

        EmailService.send_email(
            recipient=recipient,
            subject=subject,
            content=content,
        )

    except Exception as exc:

        raise self.retry(exc=exc)