from django.urls import path
from apps.realtime.consumers.tanent_consumer import TenantConsumer
from apps.realtime.consumers.PlatformConsumer import PlatformConsumer



websocket_urlpatterns = [
    path("ws/app/", TenantConsumer.as_asgi()),
    path("ws/platform/", PlatformConsumer.as_asgi()),
]