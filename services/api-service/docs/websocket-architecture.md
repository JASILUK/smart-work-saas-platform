# WebSocket Architecture

## Stack

| Component | Implementation |
|-----------|----------------|
| ASGI | `config.asgi.application` |
| Protocol router | HTTP → Django ASGI; WebSocket → auth middleware + URL router |
| Channel layer | `channels_redis.core.RedisChannelLayer` → `redis:6379` |
| Secondary Redis | Direct `redis.Redis.from_url(REDIS_URL)` in consumers/services for presence sets |

## Entry Point

```python
# config/asgi.py
ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": WebSocketAuthMiddleware(
        URLRouter(apps.chat.routing.websocket_urlpatterns)
    ),
})
```

Settings module selected via `DJANGO_ENV` (default `local`).

## Routes

| Path | Consumer | Audience |
|------|----------|----------|
| `ws/app/` | `TenantConsumer` | Company members (tenant chat) |
| `ws/platform/` | `PlatformConsumer` | Platform staff (`platform_profile`) |

**Unregistered consumers** (legacy/experimental): `chat_consumer.py`, `presence_consumer.py`, `main_consumer.py`.

## Authentication (`WebSocketAuthMiddleware`)

Priority order:

1. **Ticket** — query `?ticket=<uuid>`
   - Key: `ws_ticket_{ticket}` in Django cache (Redis DB 2)
   - Payload: `{user_id, tenant_id}` — deleted on use (one-time)
   - Issued by `POST /api/chat/v1/ws-ticket/` (`WebSocketTicketView`)

2. **JWT fallback** — query `?token=<access_jwt>`
   - Decoded with `SECRET_KEY`, HS256
   - Does not embed `tenant_id` in middleware — **tenant WS may fail membership resolution** if only JWT is used without ticket

3. **Scope population**
   - `scope["user"]`
   - `scope["tenant_id"]`
   - `scope["membership"]` — `Membership` for `(user, company_id=tenant_id)` when both present

`TenantConsumer.connect` closes connection if user anonymous, missing `tenant_id`, or missing `membership`.

## Channel Groups

| Group pattern | Purpose |
|---------------|---------|
| `tenant_{tenant_id}_user_{membership_id}` | Per-user sidebar, personal events |
| `tenant_{tenant_id}` | Tenant-wide presence |
| `tenant_{tenant_id}_room_{conversation_id}` | Room messages, typing |
| `platform_user_{user_id}` | Platform user channel |
| `platform_global` | Platform-wide broadcasts |

## Redis Keys (Presence & Rooms)

| Key | Structure | Purpose |
|-----|-----------|---------|
| `user:{membership_id}:connections` | SET of channel names | Multi-tab connection counting |
| `online_users:{tenant_id}` | SET of membership IDs | Tenant online set |
| `user:{membership_id}:last_seen` | ISO timestamp string | Fast last-seen read |
| `room:{tenant_id}:{room_id}` | SET of membership IDs | Active viewers in conversation |

## TenantConsumer Lifecycle

### Connect

1. Join `user_group` and `tenant_group`
2. Track socket in Redis connection set
3. On first connection → add to `online_users`, broadcast `presence_update`
4. Send `presence_snapshot` to client
5. `mark_all_as_delivered_on_connect` — bulk SENT → DELIVERED + status broadcasts

### Disconnect

1. Leave channel groups
2. Decrement connection set; on zero → remove from online set, update `Membership.last_seen`, broadcast `presence_update` + `last_seen_update`

### Client → Server Events (`receive`)

| `type` | Handler |
|--------|---------|
| `join_room` | Join room group; track in Redis; auto-mark room read |
| `leave_room` | Leave room group; remove from Redis room set |
| `message_received` | ACK delivery: SENT → DELIVERED |
| `mark_read` | Mark room messages read |
| `typing_start` / `typing_stop` | Broadcast to room group |

### Server → Client Handlers

| Handler | Event shape |
|---------|-------------|
| `chat_message` | New message payload |
| `incoming_message` | Alternate message envelope |
| `sidebar_update` | Conversation list row update |
| `status_update` | Per-recipient message status |
| `presence_update` | online/offline |
| `presence_snapshot` | Initial online list |
| `typing_event` | Typing indicator |
| `last_seen_update` | ISO timestamp |
| `message_deleted` / `message_edited` | Message mutations |
| `conversation_created` | New conversation for sidebar |

HTTP-initiated broadcasts use `MessageService` + `async_to_sync(channel_layer.group_send)`.

## PlatformConsumer

- Requires authenticated user with active `platform_profile`
- Joins `platform_user_{id}` and `platform_global`
- Separate from tenant membership model

## Security Considerations

| Topic | Status |
|-------|--------|
| Ticket one-time use | Good |
| JWT in query string | Log leakage risk; prefer tickets |
| Room join authorization | **Client can send arbitrary `room_id`** — server adds to group without participant check in `join_room` |
| Cross-tenant isolation | Group names include `tenant_id` from auth scope — OK if auth correct |

**Recommendation:** Validate `ConversationParticipant` exists before `group_add` in `join_room`.

## Scaling

- Horizontal scale: multiple ASGI workers + shared Redis channel layer
- Presence sets are global per tenant — consider Redis Cluster / key TTL for stale members
- `mark_all_as_delivered_on_connect` loads all SENT statuses for membership — heavy for inactive users with backlog

## Related Documents

- [websocket/websocket-events.md](./websocket/websocket-events.md)
- [websocket/realtime-message-flow.md](./websocket/realtime-message-flow.md)
- [features/chat.md](./features/chat.md)
