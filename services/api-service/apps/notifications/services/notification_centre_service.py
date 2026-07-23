from typing import Optional
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.notifications.selectors.notification_selectors import NotificationSelector
from apps.notifications.models import Notification


class NotificationCenterService:
    """
    Enterprise-grade service layer handling all Notification Center business operations.
    Exclusively consumes NotificationSelector for reads and enforces strict membership boundaries.
    """

    @staticmethod
    def list_notifications(
        *,
        membership,
        is_read: Optional[bool] = None,
        notification_type: Optional[str] = None,
        created_after=None,
        created_before=None,
        search: Optional[str] = None,
    ) -> QuerySet[Notification]:
        """
        Retrieves a filtered, ordered queryset of notifications via NotificationSelector.
        """
        return NotificationSelector.list_notifications(
            membership=membership,
            is_read=is_read,
            notification_type=notification_type,
            created_after=created_after,
            created_before=created_before,
            search=search,
        )

    @staticmethod
    def get_notification(*, membership, notification_id) -> Notification:
        """
        Retrieves a single notification belonging to the specified membership.
        """
        return NotificationSelector.get_notification(
            membership=membership,
            notification_id=notification_id,
        )

    @staticmethod
    def get_unread_count(*, membership) -> int:
        """
        Returns the count of unread notifications for the membership.
        """
        return NotificationSelector.get_unread_count(membership=membership)

    @staticmethod
    def exists(*, membership, notification_id) -> bool:
        """
        Checks whether a notification exists and belongs to the specified membership.
        """
        return NotificationSelector.exists(
            membership=membership,
            notification_id=notification_id,
        )

    @staticmethod
    @transaction.atomic
    def mark_as_read(*, membership, notification_id) -> Notification:
        """
        Marks a specific notification as read. Safely handles already-read records.
        """
        notification = NotificationSelector.get_notification(
            membership=membership,
            notification_id=notification_id,
        )

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at", "updated_at"])

        return notification

    @staticmethod
    @transaction.atomic
    def mark_all_as_read(*, membership) -> int:
        """
        Efficiently marks all unread notifications as read for the membership in bulk.
        """
        now = timezone.now()
        updated_count = Notification.objects.filter(
            membership=membership,
            is_read=False,
        ).update(
            is_read=True,
            read_at=now,
        )
        return updated_count

    @staticmethod
    @transaction.atomic
    def delete_notification(*, membership, notification_id) -> None:
        """
        Deletes a single notification after validating strict ownership via the selector.
        """
        notification = NotificationSelector.get_notification(
            membership=membership,
            notification_id=notification_id,
        )
        notification.delete()

    @staticmethod
    @transaction.atomic
    def clear_read_notifications(*, membership) -> int:
        """
        Deletes all read notifications for the membership in bulk.
        """
        deleted_count, _ = Notification.objects.filter(
            membership=membership,
            is_read=True,
        ).delete()
        return deleted_count