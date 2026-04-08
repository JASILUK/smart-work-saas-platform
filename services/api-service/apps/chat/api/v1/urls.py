from django.urls import path
from .views import (
    ConversationListView,
    ConversationMessagesView,
    DirectChatView,
    MarkAsReadView,
    SendMessageView,
    WebSocketTicketView,
)

urlpatterns = [
    path("conversations/", ConversationListView.as_view()),
    path("conversations/<uuid:conversation_id>/read/", MarkAsReadView.as_view()),
    path("direct/", DirectChatView.as_view()),
    path(
        "messages/<uuid:conversation_id>/",
        ConversationMessagesView.as_view(),
        name="conversation-messages",
    ),
    path("send-message/", SendMessageView.as_view()),
    path("ws-ticket/", WebSocketTicketView.as_view(), name="ws-ticket"),
]