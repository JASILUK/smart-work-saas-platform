import logging

from celery import shared_task

from apps.users.services.notification import NotificationService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def send_notification_task(
    self,
    *,
    channel,
    recipient,
    template_name=None,
    context=None,
    content=None,
    subject=None,
):
    """
    Background task for sending notifications
    """

    try:

        service = NotificationService()

        service.send_notification(
            channel=channel,
            recipient=recipient,
            template_name=template_name,
            context=context,
            content=content,
            subject=subject,
        )

        logger.info(f"Notification sent via {channel} to {recipient}")

    except Exception as exc:

        logger.error(f"Notification failed for {recipient}: {exc}")

        raise exc
