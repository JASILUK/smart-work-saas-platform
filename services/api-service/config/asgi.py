import os
import django

from dotenv import load_dotenv
load_dotenv()
env = os.environ.get("DJANGO_ENV", "local")


os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"config.settings.{env}")

django.setup()  # 🔥 VERY IMPORTANT

from channels.routing import ProtocolTypeRouter, URLRouter
from apps.realtime.middlewares.websocket_auth import WebSocketAuthMiddleware
import apps.realtime.routing
from django.core.asgi import get_asgi_application

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,

    "websocket": WebSocketAuthMiddleware(
        URLRouter(
            apps.realtime.routing.websocket_urlpatterns
        )
    ),
})

