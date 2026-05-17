# WebSocket Channel Groups

Django Channels group names determine broadcast scope. All tenant groups include `tenant_id` from authenticated scope (company PK).

## Tenant Groups

| Pattern | Members | Used for |
|---------|---------|----------|
| `tenant_{tenant_id}_user_{membership_id}` | All sockets for one membership | Sidebar updates, personal message copies |
| `tenant_{tenant_id}` | All connected tenant users | Presence online/offline |
| `tenant_{tenant_id}_room_{conversation_id}` | Users who called `join_room` | Live messages, typing |

## Platform Groups

| Pattern | Used for |
|---------|----------|
| `platform_user_{user_id}` | Platform staff user channel |
| `platform_global` | Broadcast to all platform connections |

## Redis Structures (Non-Channels)

| Key | Type | Purpose |
|-----|------|---------|
| `user:{membership_id}:connections` | SET | Socket channel names for tab counting |
| `online_users:{tenant_id}` | SET | Online membership IDs |
| `room:{tenant_id}:{room_id}` | SET | Membership IDs currently viewing conversation |
| `user:{membership_id}:last_seen` | STRING | ISO timestamp cache |

## Join / Leave Rules

- **User/tenant groups:** joined on connect, discarded on disconnect
- **Room groups:** joined on client `join_room`, left on `leave_room` or disconnect (room discard only on explicit leave — verify disconnect behavior)

On disconnect, user/tenant groups are always discarded; room group may linger until explicit leave (connection drop does not call `leave_room`).

## Message Routing Example

New message in conversation `C`:

1. `group_send` to `tenant_{t}_room_{C}` → active viewers
2. `group_send` to each `tenant_{t}_user_{recipient}` → sidebar + notification UX
3. Status updates to participants' user groups

## Scaling Note

Group fan-out cost grows with:

- Tenant connections (presence broadcasts)
- Room members (typing, messages)
- Group chat participant count

## Security Note

Group names are predictable if UUIDs leak. Authorization must happen before `group_add` — see [../security-considerations.md](../security-considerations.md).
