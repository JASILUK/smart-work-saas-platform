# Chat API

Base path: `/api/chat/v1/`

**Required header:** `X-Company-ID`  
**Auth:** JWT cookie or Bearer

## Conversations

| Method | Path | Description |
|--------|------|-------------|
| GET | `conversations/` | List conversations for `request.membership` |
| GET | `conversations/<uuid>/messages/` | Paginated messages; query cursor params per view |
| POST | `conversations/<uuid>/read/` | HTTP mark-as-read |

## Direct Messages

| Method | Path | Description |
|--------|------|-------------|
| POST | `direct/` | Create or get DM with target membership/user |

## Messages

| Method | Path | Description |
|--------|------|-------------|
| POST | `messages/send/` | Send text/media; multipart for files |
| PATCH | `messages/<uuid>/` | Edit (if supported by view) |
| DELETE | `messages/<uuid>/` | Soft delete |
| GET | `messages/<uuid>/info/` | Read/delivery receipt details |

### Send body (typical)

- `conversation_id`
- `content` (text)
- `file` (optional)
- `reply_to_id` (optional)

## Groups

| Method | Path | Description |
|--------|------|-------------|
| POST | `groups/` | Create group conversation |
| GET | `groups/<uuid>/` | Group metadata + participants |
| POST | `groups/<uuid>/members/` | Add members |
| POST | `groups/<uuid>/members/remove/` | Remove member |
| POST | `groups/<uuid>/leave/` | Leave group |
| PATCH | `groups/<uuid>/roles/` | Change participant chat role |
| PATCH | `groups/<uuid>/settings/` | Name, avatar, description |

## WebSocket Ticket

| Method | Path | Description |
|--------|------|-------------|
| POST | `ws-ticket/` | Returns `{ticket, expires}` for `ws/app/?ticket=` |

Ticket stored in Redis cache; single use.

## WebSocket Usage

After ticket:

```
wss://<host>/ws/app/?ticket=<uuid>
```

Then send JSON commands per [../websocket/websocket-events.md](../websocket/websocket-events.md).

## Permissions

Inherits company + subscription stack. Individual views may add `required_permissions` — check view classes in `apps/chat/api/v1/views.py`.

Message authorization primarily **participant-based** in services.

## Related

- [../features/chat.md](../features/chat.md)
- [../websocket/realtime-message-flow.md](../websocket/realtime-message-flow.md)
