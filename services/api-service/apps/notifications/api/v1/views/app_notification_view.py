from rest_framework import status

from apps.core.api_response import ApiResponse
from apps.core.standers_pagination import StandardLimitOffsetPagination, PaginationAdapter
from apps.companies.api.base import BaseCompanyAPIView
from apps.notifications.services.notification_centre_service import NotificationCenterService
from apps.notifications.api.v1.serializers import (
    NotificationSerializer,
    NotificationDetailSerializer,
    NotificationUnreadCountSerializer,
    NotificationListQuerySerializer,
    NotificationReadAllSerializer,
    NotificationClearReadSerializer,
)


class NotificationListView(BaseCompanyAPIView):
    pagination_class = StandardLimitOffsetPagination

    def get(self, request):
        query_serializer = NotificationListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        notifications = NotificationCenterService.list_notifications(
            membership=request.membership,
            **query_serializer.validated_data,
        )

        paginator = self.pagination_class()
        paginated_notifications = paginator.paginate_queryset(notifications, request, view=self)
        serializer = NotificationSerializer(paginated_notifications, many=True)
        
        pagination_metadata = PaginationAdapter.adapt(paginator, request=request)

        return ApiResponse.success(
            data={
                "results": serializer.data,
                "pagination": pagination_metadata,
            }
        )


class NotificationUnreadCountView(BaseCompanyAPIView):
    def get(self, request):
        unread_count = NotificationCenterService.get_unread_count(membership=request.membership)
        serializer = NotificationUnreadCountSerializer({"unread_count": unread_count})
        return ApiResponse.success(data=serializer.data)


class NotificationReadAllView(BaseCompanyAPIView):
    def patch(self, request):
        updated_count = NotificationCenterService.mark_all_as_read(membership=request.membership)
        serializer = NotificationReadAllSerializer({"updated_count": updated_count})
        return ApiResponse.success(
            message="All notifications marked as read successfully.",
            data=serializer.data,
        )


class NotificationClearReadView(BaseCompanyAPIView):
    def delete(self, request):
        deleted_count = NotificationCenterService.clear_read_notifications(membership=request.membership)
        serializer = NotificationClearReadSerializer({"deleted_count": deleted_count})
        return ApiResponse.success(
            message="Read notifications cleared successfully.",
            data=serializer.data,
        )


class NotificationReadView(BaseCompanyAPIView):
    def patch(self, request, notification_id):
        notification = NotificationCenterService.mark_as_read(
            membership=request.membership,
            notification_id=notification_id,
        )
        serializer = NotificationDetailSerializer(notification)
        return ApiResponse.success(
            message="Notification marked as read successfully.",
            data=serializer.data,
        )


class NotificationDetailView(BaseCompanyAPIView):
    def get(self, request, notification_id):
        notification = NotificationCenterService.get_notification(
            membership=request.membership,
            notification_id=notification_id,
        )
        serializer = NotificationDetailSerializer(notification)
        return ApiResponse.success(data=serializer.data)

    def delete(self, request, notification_id):
        NotificationCenterService.delete_notification(
            membership=request.membership,
            notification_id=notification_id,
        )
        return ApiResponse.success(
            message="Notification deleted successfully.",
            status=status.HTTP_204_NO_CONTENT,
        )