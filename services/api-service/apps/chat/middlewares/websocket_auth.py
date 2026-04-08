from urllib.parse import parse_qs
from django.core.cache import cache
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

User = get_user_model()

class WebSocketAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = parse_qs(scope["query_string"].decode())
        ticket = query_string.get("ticket")

        if ticket:
            ticket_key = f"ws_ticket_{ticket[0]}"

            user_id = await sync_to_async(cache.get)(ticket_key)

            if user_id:
                try:
                    scope["user"] = await sync_to_async(User.objects.get)(id=user_id)
                except User.DoesNotExist:
                    scope["user"] = AnonymousUser()

                # 🔥 IMPORTANT: delete ticket (one-time use)
                await sync_to_async(cache.delete)(ticket_key)

                return await super().__call__(scope, receive, send)

        # fallback
        scope["user"] = scope.get("user", AnonymousUser())
        return await super().__call__(scope, receive, send)