from urllib.parse import parse_qs
from django.core.cache import cache
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
import jwt

from apps.companies.models import Membership  # ✅ IMPORTANT

User = get_user_model()


@sync_to_async
def get_user_by_id(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


@sync_to_async
def get_membership(user, tenant_id):
    try:
        return Membership.objects.select_related("user").get(
            user=user,
            company_id=tenant_id
        )
    except Membership.DoesNotExist:
        return None


class WebSocketAuthMiddleware(BaseMiddleware):

    async def __call__(self, scope, receive, send):
        query_string = parse_qs(scope["query_string"].decode())

        user = None
        tenant_id = None

        # =========================
        # 1️⃣ TICKET AUTH
        # =========================
        ticket = query_string.get("ticket")

        if ticket:
            ticket_key = f"ws_ticket_{ticket[0]}"
            ticket_data = await sync_to_async(cache.get)(ticket_key)

            if ticket_data:
                user = await get_user_by_id(ticket_data["user_id"])
                tenant_id = ticket_data.get("tenant_id")

                await sync_to_async(cache.delete)(ticket_key)

        # =========================
        # 2️⃣ JWT FALLBACK
        # =========================
        if not user or user.is_anonymous:
            token = query_string.get("token")

            if token:
                try:
                    payload = jwt.decode(
                        token[0],
                        settings.SECRET_KEY,
                        algorithms=["HS256"]
                    )
                    user = await get_user_by_id(payload.get("user_id"))

                except:
                    user = AnonymousUser()

        # =========================
        # 3️⃣ FINAL ASSIGN
        # =========================
        scope["user"] = user if user else AnonymousUser()
        scope["tenant_id"] = tenant_id

        # =========================
        # 4️⃣ 🔥 FIX: ADD MEMBERSHIP
        # =========================
        if user and not user.is_anonymous and tenant_id:
            membership = await get_membership(user, tenant_id)
            scope["membership"] = membership
        else:
            scope["membership"] = None

        return await super().__call__(scope, receive, send)