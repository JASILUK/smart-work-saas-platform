from django.db.models.signals import post_save

from django.dispatch import receiver

from apps.companies.models import Membership

from apps.notifications.models import (
    NotificationPreference,
)


@receiver(post_save, sender=Membership)
def create_notification_preferences(
    sender,
    instance,
    created,
    **kwargs,
):

    if not created:
        return

    NotificationPreference.objects.create(
        membership=instance
    )