# Notification Events (Push)

WebSockets deliver in-app realtime; **push notifications** use FCM through a separate pipeline.

## Trigger: Chat Message

```
MessageService._send_notifications
  → For each recipient membership (not sender, not online in room):
       NotificationService.send_chat_notification
         → create_notification (DB row, type=CHAT)
         → check NotificationPreference (push_enabled, chat_message_enabled)
         → PushService.send_push_notification
              → Celery task
              → FirebaseProvider
```

## Payload Construction

`apps/notifications/utils/payload_builder.py` shapes FCM data payload including:

- `conversation_id` / `message_id` / `sender_membership_id` (in `Notification.data` JSON)

Clients use data keys for deep linking.

## Preference Gates

| Toggle | Blocks |
|--------|--------|
| `push_enabled` | All push |
| `chat_message_enabled` | Chat push only |
| `meeting_enabled` | Meeting push (sender exists; no producer) |
| `attendance_enabled` | Not wired |
| `mention_enabled` | Mention push (verify producer) |
| `system_enabled` | System push |

DB notification may still be created when push skipped — chat flow creates DB record before preference check for push only on chat path (verify `send_chat_notification` — creates DB first, then checks prefs for push).

## Device Targeting

`PushService` loads active `NotificationDevice` rows for `membership` with valid FCM `token`.

## Failure Modes

- Invalid token → should deactivate device (verify `push_tasks` behavior)
- Firebase init failure at startup → push silently fails if not caught
- Celery down → notifications persist in DB without push

## Not WebSocket Events

Push does not emit channel layer events. Clients receive FCM/APNs on device OS.

## Future: Meeting Notifications

`send_meeting_notification` exists — wire when meetings feature ships.

## Related

- [../features/notifications.md](../features/notifications.md)
- [../api/notifications-api.md](../api/notifications-api.md)
