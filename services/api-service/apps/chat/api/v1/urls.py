# apps/chat/api/v1/urls.py

from django.urls import path

from apps.chat.api.v1.views import (
    ConversationListView,
    ConversationMessagesView,
    DirectChatView,
    MarkAsReadView,
    MessageDetailView,
    MessageInfoView,
    SendMessageView,
    WebSocketTicketView,
)

from apps.chat.api.v1.views import (
    CreateGroupView,
    GroupDetailsView,
    AddMembersView,
    RemoveMemberView,
    LeaveGroupView,
    UpdateRoleView,
    UpdateGroupView,
)

urlpatterns = [

    # conversations
    path(
        "conversations/",
        ConversationListView.as_view(),
        name="conversation-list",
    ),

    path(
        "conversations/<uuid:conversation_id>/messages/",
        ConversationMessagesView.as_view(),
        name="conversation-messages",
    ),

    path(
        "conversations/<uuid:conversation_id>/read/",
        MarkAsReadView.as_view(),
        name="mark-as-read",
    ),

    # direct chat
    path(
        "direct/",
        DirectChatView.as_view(),
        name="direct-chat",
    ),

    # messages
    path(
        "messages/send/",
        SendMessageView.as_view(),
        name="send-message",
    ),

    path(
        "messages/<uuid:message_id>/",
        MessageDetailView.as_view(),
        name="message-detail",
    ),



    path(
        "messages/<uuid:message_id>/info/",
        MessageInfoView.as_view(),
        name="message-info",
    ),

    # groups
    path(
        "groups/",
        CreateGroupView.as_view(),
        name="create-group",
    ),

    path(
        "groups/<uuid:conversation_id>/",
        GroupDetailsView.as_view(),
        name="group-details",
    ),

    path(
        "groups/<uuid:conversation_id>/members/",
        AddMembersView.as_view(),
        name="add-members",
    ),

    path(
        "groups/<uuid:conversation_id>/members/remove/",
        RemoveMemberView.as_view(),
        name="remove-member",
    ),

    path(
        "groups/<uuid:conversation_id>/leave/",
        LeaveGroupView.as_view(),
        name="leave-group",
    ),

    path(
        "groups/<uuid:conversation_id>/roles/",
        UpdateRoleView.as_view(),
        name="update-role",
    ),

    path(
        "groups/<uuid:conversation_id>/settings/",
        UpdateGroupView.as_view(),
        name="update-group",
    ),





    # websocket
    path(
        "ws-ticket/",
        WebSocketTicketView.as_view(),
        name="ws-ticket",
    ),
]