from apps.chat.api.v1.serializers import (
    AddMembersSerializer,
    ConversationSerializer,
    CreateGroupSerializer,
    GroupDetailsSerializer,
    GroupResponseSerializer,
    MessageInfoSerializer,
    MessageSerializer,
    DirectChatSerializer,
    RemoveMemberSerializer,
    SendMessageSerializer,
    UpdateGroupSerializer,
    UpdateRoleSerializer,
)
from apps.chat.services.group_service import GroupService
from rest_framework.views import APIView

from apps.chat.services.chat_service import ChatService
from apps.chat.services.message_service import MessageService

from apps.companies.api.base import BaseCompanyAPIView
from apps.core.api_response import ApiResponse

from rest_framework import status


import uuid
from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

class ChatPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"



class ConversationListView(BaseCompanyAPIView):

    def get(self, request):

        search = request.query_params.get(
            "search",
            "",
        )

        conversation_type = request.query_params.get(
            "type",
            "all",
        )

        conversations = (
            ChatService.list_conversations(
                membership=request.membership,
                search=search,
                conversation_type=conversation_type,
            )
        )

        serializer = ConversationSerializer(
            conversations,
            many=True,
            context={
                "request": request,
            },
        )

        return ApiResponse.success(
            data=serializer.data,
        )


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
    parser_classes = [MultiPartParser, FormParser , JSONParser]

    def post(self, request):
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = MessageService.send_message(
            conversation_id=serializer.validated_data["conversation_id"],
            sender_membership=request.membership,
            content=serializer.validated_data.get("content"),
            file=serializer.validated_data.get("file"),
            reply_to_id=serializer.validated_data.get("reply_to_id"),
        )

        return ApiResponse.success(
            data=MessageSerializer(
                message,
                context={"request": request},
            ).data
        )

class MessageDetailView(BaseCompanyAPIView):

    def delete(self, request, message_id):
        try:
            message = MessageService.delete_message(
                message_id=message_id,
                membership=request.membership,
            )

            return ApiResponse.success(data={
                "message_id": str(message.id),
                "deleted": True
            })

        except Exception as e:
            return ApiResponse.error(message=str(e))
    
    def patch(self, request, message_id):
        content = request.data.get("content")

        if not content:
            return ApiResponse.error(message="Content required")

        message = MessageService.edit_message(
            message_id=message_id,
            membership=request.membership,
            new_content=content,
        )

        return ApiResponse.success(data={
            "message_id": str(message.id),
            "content": message.content,
            "edited": True
        })
    

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
    





class CreateGroupView(BaseCompanyAPIView):

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):

        serializer = CreateGroupSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        conversation = GroupService.create_group(
            creator_membership=request.membership,
            **serializer.validated_data,
        )

        response_serializer = GroupResponseSerializer(
            conversation
        )

        return ApiResponse.success(
            data=response_serializer.data,
            status_code=status.HTTP_201_CREATED,
        )
    

class GroupDetailsView(BaseCompanyAPIView):

    def get(self, request, conversation_id):

        conversation = GroupService.get_group_details(
            conversation_id=conversation_id,
            membership=request.membership,
        )

        serializer = GroupDetailsSerializer(
            conversation
        )

        return ApiResponse.success(
            data=serializer.data
        )


class AddMembersView(BaseCompanyAPIView):

    def post(self, request, conversation_id):

        serializer = AddMembersSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        GroupService.add_members(
            conversation_id=conversation_id,
            actor_membership=request.membership,
            member_ids=serializer.validated_data["member_ids"],
        )

        return ApiResponse.success(
            message="Members added successfully"
        )


class RemoveMemberView(BaseCompanyAPIView):

    def post(self, request, conversation_id):

        serializer = RemoveMemberSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        GroupService.remove_member(
            conversation_id=conversation_id,
            actor_membership=request.membership,
            target_membership_id=serializer.validated_data["membership_id"],
        )

        return ApiResponse.success(
            message="Member removed successfully"
        )


class LeaveGroupView(BaseCompanyAPIView):

    def post(self, request, conversation_id):

        GroupService.leave_group(
            conversation_id=conversation_id,
            membership=request.membership,
        )

        return ApiResponse.success(
            message="Group left successfully"
        )


class UpdateRoleView(BaseCompanyAPIView):

    def patch(self, request, conversation_id):

        serializer = UpdateRoleSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        participant = GroupService.update_role(
            conversation_id=conversation_id,
            actor_membership=request.membership,
            target_membership_id=serializer.validated_data["membership_id"],
            role=serializer.validated_data["role"],
        )

        return ApiResponse.success(
            data={
                "membership_id": participant.membership_id,
                "role": participant.chat_role,
            },
            message="Role updated successfully",
        )


class UpdateGroupView(BaseCompanyAPIView):

    parser_classes = [ MultiPartParser, FormParser, JSONParser, ]

    def patch(self, request, conversation_id):

        serializer = UpdateGroupSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        conversation = GroupService.update_group(
            conversation_id=conversation_id,
            actor_membership=request.membership,
            **serializer.validated_data,
        )

        response_serializer = GroupResponseSerializer(
            conversation
        )

        return ApiResponse.success(
            data=response_serializer.data,
            message="Group updated successfully",
        )




class MessageInfoView(BaseCompanyAPIView):

    def get(self, request, message_id):

        data = MessageService.get_message_info(
            message_id=message_id,
            membership=request.membership,
        )

        serializer = MessageInfoSerializer(data)

        return ApiResponse.success(
            data=serializer.data
            )