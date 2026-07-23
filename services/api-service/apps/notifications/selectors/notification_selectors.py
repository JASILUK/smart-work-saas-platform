from typing import Optional
from django.db.models import QuerySet, Q
from django.shortcuts import get_object_or_404
from apps.notifications.models import Notification


class NotificationSelector:
    """
    Selector pattern implementation for Notification read operations.
    Enforces strict membership isolation, query optimization, and enterprise scalability.
    """

    @staticmethod
    def _base_queryset(*, membership) -> QuerySet[Notification]:
        """
        Private base queryset builder ensuring membership boundary enforcement
        and enterprise-grade column optimization.
        """
        return Notification.objects.filter(membership=membership).only(
            "id",
            "membership_id",
            "type",
            "title",
            "body",
            "data",
            "is_read",
            "read_at",
            "created_at",
        )

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
        Returns a filtered, ordered notification queryset for a membership.
        Supports pagination and flexible multi-parameter filtering.
        """
        qs = NotificationSelector._base_queryset(membership=membership)

        if is_read is not None:
            qs = qs.filter(is_read=is_read)

        if notification_type:
            qs = qs.filter(type=notification_type)

        if created_after:
            qs = qs.filter(created_at__gte=created_after)

        if created_before:
            qs = qs.filter(created_at__lte=created_before)

        if search:
            qs = qs.filter(
                Q(title__icontains=search) | Q(body__icontains=search)
            )

        return qs.order_by("-created_at")

    @staticmethod
    def get_notification(*, membership, notification_id) -> Notification:
        """
        Returns a single notification strictly owned by the membership.
        Raises Http404 if not found or unauthorized.
        """
        return get_object_or_404(
            NotificationSelector._base_queryset(membership=membership),
            id=notification_id,
        )

    @staticmethod
    def get_unread_count(*, membership) -> int:
        """
        Returns an optimized database count of unread notifications for a membership.
        """
        return Notification.objects.filter(
            membership=membership,
            is_read=False,
        ).count()

    @staticmethod
    def list_unread_notifications(*, membership) -> QuerySet[Notification]:
        """
        Returns only unread notifications for a membership, newest first.
        """
        return NotificationSelector.list_notifications(
            membership=membership,
            is_read=False,
        )

    @staticmethod
    def list_read_notifications(*, membership) -> QuerySet[Notification]:
        """
        Returns only read notifications for a membership, newest first.
        """
        return NotificationSelector.list_notifications(
            membership=membership,
            is_read=True,
        )

    @staticmethod
    def list_notifications_by_type(*, membership, notification_type: str) -> QuerySet[Notification]:
        """
        Returns notifications filtered by a specific type (e.g. chat, meeting, system, mention), newest first.
        """
        return NotificationSelector.list_notifications(
            membership=membership,
            notification_type=notification_type,
        )

    @staticmethod
    def list_recent_notifications(*, membership, limit: int = 10) -> QuerySet[Notification]:
        """
        Returns the most recent notifications for a membership, optimized for UI dropdowns/navbars.
        """
        return NotificationSelector.list_notifications(membership=membership)[:limit]

    @staticmethod
    def exists(*, membership, notification_id) -> bool:
        """
        Checks efficiently whether a notification exists and belongs to the given membership.
        """
        return Notification.objects.filter(
            id=notification_id,
            membership=membership,
        ).exists()