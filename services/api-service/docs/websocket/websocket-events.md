# WebSocket Events Reference

## Connection

| Parameter | Required | Description |
|-----------|----------|-------------|
| `ticket` | Preferred | One-time key from `POST /api/chat/v1/ws-ticket/` |
| `token` | Fallback | JWT access token (tenant_id may be missing) |

**Tenant URL:** `ws/app/`  
**Platform URL:** `ws/platform/`

## Client → Server

| `type` | Payload fields | Effect |
|--------|----------------|--------|
| `join_room` | `room_id` (conversation UUID) | Join `tenant_{tid}_room_{room_id}`; add to Redis room set; mark messages read |
| `leave_room` | `room_id` | Leave group; remove from Redis set |
| `message_received` | `message_id` | SENT → DELIVERED for acking client |
| `mark_read` | `room_id` | Mark all non-read statuses in room as READ |
| `typing_start` | `room_id` | Broadcast typing true |
| `typing_stop` | `room_id` | Broadcast typing false |

## Server → Client (TenantConsumer)

| `type` / handler | Description |
|------------------|-------------|
| `presence_snapshot` | `{type, users: [membership_ids]}` on connect |
| `presence_update` | `{type, user_id, status: online\|offline}` |
| `last_seen_update` | `{type, user_id, last_seen: ISO8601}` |
| `typing_event` | `{type, user_id, room_id, is_typing}` |
| `sidebar_update` | Conversation list delta |
| `status_update` | Message receipt aggregate per message |
| `chat_message` | New message in room |
| `incoming_message` | Message envelope for recipient UX |
| `message_edited` | Edit broadcast |
| `message_deleted` | Delete broadcast |
| `conversation_created` | New conversation for sidebar |

Exact payload shapes are built in `MessageService._broadcast_message` and group services — clients should treat unknown fields as forward-compatible.

## HTTP-Originated Events

Same handler names used when `channel_layer.group_send` is called from sync services with `"type": "<handler_name>"`.

## Platform Consumer

Separate event set on `platform_user_*` and `platform_global` groups — inspect `PlatformConsumer.py` for platform-specific handlers.

## Error Handling

Consumer catches exceptions in `connect`, `disconnect`, `receive` and logs via `print` — clients may see abrupt close without error body.

## Related

- [websocket-groups.md](./websocket-groups.md)
- [realtime-message-flow.md](./realtime-message-flow.md)
