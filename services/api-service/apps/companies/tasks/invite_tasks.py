import logging

from celery import shared_task
from django.conf import settings

from apps.companies.models import CompanyInvite
from apps.users.services.notification import NotificationService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def send_invite_email_task(self, invite_id, raw_secret):

    try:
        invite = CompanyInvite.objects.select_related("company").get(id=invite_id)

        invite_link = (
            f"{settings.FRONTEND_URL}/invite" f"?token={invite.token_id}.{raw_secret}"
        )

        context = {
            "company_name": invite.company.name,
            "invite_link": invite_link,
            "expiry_hours": 48,
        }

        NotificationService().send_notification(
            channel="EMAIL",
            recipient=invite.email,
            template_name="company_invite",
            context=context,
            subject=f"You are invited to join {invite.company.name}",
        )

    except Exception as exc:
        logger.error(f"Invite email failed for invite {invite_id}: {exc}")
        raise exc
