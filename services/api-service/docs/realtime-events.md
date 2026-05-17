# Realtime Events

## Event Sources

| Source | Mechanism |
|--------|-----------|
| HTTP `MessageService` | `channel_layer.group_send` after DB commit |
| `TenantConsumer` | Client-driven ACKs, read receipts, typing, presence |
| `group_realtime_service` | Group lifecycle sidebar/conversation events |
| `department_chat_service` | Department member sync to conversation participants |

## Event Categories

### 1. Message Events

Emitted on send, edit, delete from HTTP services.

| Channel handler | Typical `type` in JSON |
|-----------------|------------------------|
| `chat_message` | Full message payload to room + user groups |
| `incoming_message` | Recipient-focused envelope |
| `message_edited` | Updated content/metadata |
| `message_deleted` | Soft-delete notification |

Delivery pipeline:

1. Create `Message` + `MessageStatus` per participant (sender excluded or special-cased)
2. Increment `ConversationParticipant.unread_count` for recipients
3. Update `Conversation.last_message`
4. Broadcast to `tenant_{id}_room_{conversation_id}` and per-user groups
5. Offline users → `NotificationService.send_chat_notification` → FCM

### 2. Status Events

| Trigger | Transition |
|---------|------------|
| WS connect | All SENT → DELIVERED for membership |
| Client `message_received` | SENT → DELIVERED for one message |
| `join_room` / `mark_read` | SENT/DELIVERED → READ |

Handler: `status_update` via `MessageService.broadcast_status_update`.

### 3. Sidebar Events

`sidebar_update` — conversation list row changes:

- `conversation_id`, `last_message` preview string, `updated_at`, `unread_count`

Triggered on send, read, group changes.

### 4. Presence Events

| Event | When |
|-------|------|
| `presence_snapshot` | On WS connect — list of online membership IDs |
| `presence_update` | Member online/offline |
| `last_seen_update` | On disconnect after last socket closes |

State stored in Redis sets + `Membership.last_seen` in PostgreSQL.

### 5. Typing Events

`typing_event` — `{user_id, room_id, is_typing}` to room group only.

### 6. Conversation Lifecycle

`conversation_created` — new direct/group/department conversation visible in sidebar.

## Client Protocol (Tenant WebSocket)

Connect: `wss://host/ws/app/?ticket=<one-time-ticket>`

Outbound JSON messages:

```json
{"type": "join_room", "room_id": "<uuid>"}
{"type": "leave_room", "room_id": "<uuid>"}
{"type": "message_received", "message_id": "<uuid>"}
{"type": "mark_read", "room_id": "<uuid>"}
{"type": "typing_start", "room_id": "<uuid>"}
{"type": "typing_stop", "room_id": "<uuid>"}
```

Inbound: server echoes event dicts with `type` field matching handler names.

## Ordering & Consistency

- **No global ordering guarantee** across rooms
- Per-conversation order: `Message.created_at` + cursor pagination on HTTP
- Read state is **per membership**, not per user account globally

## Push vs WebSocket

| Channel | When used |
|---------|-----------|
| WebSocket | Active connection in tenant |
| FCM push | `PushService` when preferences allow and device registered |
| DB `Notification` | Always created for chat notifications (even if push disabled) |

## Related Documents

- [websocket/websocket-events.md](./websocket/websocket-events.md)
- [websocket/realtime-message-flow.md](./websocket/realtime-message-flow.md)
- [websocket/notification-events.md](./websocket/notification-events.md)
