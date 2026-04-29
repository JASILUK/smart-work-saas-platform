from apps.chat.api.v1.serializers import (
    ConversationSerializer,
    MessageSerializer,
    DirectChatSerializer,
    SendMessageSerializer,
)
from rest_framework.views import APIView

from apps.chat.services.chat_service import ChatService
from apps.chat.services.message_service import MessageService

from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse

import uuid
from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

class ChatPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"


class ConversationListView(BaseCompanyAPIView):

    def get(self, request):
        conversations = ChatService.list_conversations(
            membership=request.membership
        )

        serializer = ConversationSerializer(
            conversations,
            many=True,
            context={"request": request},
        )

        return ApiResponse.success(data=serializer.data)


class DirectChatView(BaseCompanyAPIView):

    def post(self, request):
        serializer = DirectChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation = ChatService.get_or_create_direct_conversation(
            current_membership=request.membership,
            target_membership_id=serializer.validated_data["target_membership_id"],
        )

        return ApiResponse.success(data={
            "conversation_id": conversation.id
        })


class ConversationMessagesView(BaseCompanyAPIView):

    def get(self, request, conversation_id):
        cursor = request.query_params.get("cursor")
        limit = int(request.query_params.get("limit", 20))

        messages, next_cursor, has_more = MessageService.get_paginated_messages(
            conversation_id=conversation_id,
            membership=request.membership,
            cursor=cursor,
            limit=limit,
        )

        serializer = MessageSerializer(
            messages,
            many=True,
            context={"request": request},
        )

        return ApiResponse.success(data={
            "results": serializer.data,
            "next_cursor": next_cursor,
            "has_more": has_more,
        })


class SendMessageView(BaseCompanyAPIView):

    def post(self, request):
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = MessageService.send_message(
            conversation_id=serializer.validated_data["conversation_id"],
            sender_membership=request.membership,
            content=serializer.validated_data["content"],
        )

        return ApiResponse.success(
            data=MessageSerializer(
                message,
                context={"request": request},
            ).data
        )


class WebSocketTicketView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tenant_id = request.headers.get("X-Company-ID")

        ticket = str(uuid.uuid4())

        cache.set(
            f"ws_ticket_{ticket}",
            {
                "user_id": request.user.id,
                "tenant_id": tenant_id, 
            },
            timeout=30,
        )

        return ApiResponse.success(data={"ticket": ticket})


class MarkAsReadView(BaseCompanyAPIView):

    def post(self, request, conversation_id):
        MessageService.mark_conversation_as_read(
            conversation_id=conversation_id,
            membership=request.membership,
        )
        return ApiResponse.success(message="Messages marked as read")