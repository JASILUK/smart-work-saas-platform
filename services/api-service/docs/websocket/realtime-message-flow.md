# Realtime Message Flow

## End-to-End: Send Message

```
Client HTTP POST /api/chat/v1/messages/send/
  → MessageService.send_message (transaction)
       → INSERT Message
       → bulk_create MessageStatus (sender=READ, others=SENT)
       → UPDATE ConversationParticipant.unread (if not in Redis room set)
       → UPDATE Conversation.last_message
       → _broadcast_message → channel_layer
       → _send_notifications → NotificationService (offline)
  → HTTP 200 + message JSON

Parallel WS path for recipients:
  channel_layer → TenantConsumer.chat_message / incoming_message
  → Client UI updates thread

Recipient in room (Redis set):
  → unread NOT incremented
  → join_room may have marked prior messages read

Recipient WS connected, not in room:
  → unread incremented
  → sidebar_update via user group on read/send events

Recipient offline:
  → FCM push if preferences allow
  → Notification row created
```

## Delivery ACK Flow

```
Server creates MessageStatus=SENT for recipient
  → Client receives chat_message via WS or fetches via HTTP
  → Client sends {type: message_received, message_id}
  → TenantConsumer: SENT → DELIVERED
  → MessageService.broadcast_status_update
  → Other clients receive status_update
```

## Read Flow

```
Client join_room OR mark_read OR HTTP mark read
  → MessageStatus SENT/DELIVERED → READ
  → ConversationParticipant.unread_count = 0
  → sidebar_update to user group
  → status_update per affected message
```

## Connect Sync

On WebSocket connect:

1. `presence_snapshot` sent
2. All SENT statuses for membership → DELIVERED (bulk)
3. `status_update` broadcast for each distinct message

Heavy for accounts with large unread backlog.

## Edit / Delete

HTTP `MessageService` paths broadcast `message_edited` / `message_deleted` to room and user groups; sidebar preview updated similarly to send.

## Group System Messages

`system_message_service` creates `Message` with `message_type=SYSTEM` and `system_event_type` — broadcast via same channel machinery.

## Consistency Model

- **Source of truth:** PostgreSQL
- **Realtime:** best-effort via Redis channel layer
- Clients must reconcile via HTTP history on reconnect gaps

## Related

- [../features/chat.md](../features/chat.md)
- [notification-events.md](./notification-events.md)
