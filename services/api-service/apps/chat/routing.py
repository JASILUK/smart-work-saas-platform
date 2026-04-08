from django.urls import re_path

from apps.chat.consumers.main_consumer import MainConsumer
from apps.chat.consumers.presence_consumer import PresenceConsumer
from .consumers.chat_consumer import ChatConsumer

websocket_urlpatterns = [
    # re_path(r"ws/chat/(?P<conversation_id>[0-9a-f-]+)/$", ChatConsumer.as_asgi()),
    re_path(r"ws/presence/(?P<membership_id>\d+)/$",PresenceConsumer.as_asgi()),
    re_path(r"ws/chat/(?P<membership_id>\d+)/$",MainConsumer.as_asgi()),
    


]