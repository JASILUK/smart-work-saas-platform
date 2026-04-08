from django.contrib import admin
from apps.chat.models import Conversation, ConversationParticipant, Message, MessageStatus


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "type", "company", "created_at")
    search_fields = ("id",)


@admin.register(ConversationParticipant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("conversation", "membership", "chat_role")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "content", "created_at")


admin.site.register(MessageStatus)