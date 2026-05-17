# Notifications

## Purpose

Per-membership push notification infrastructure: device registration (FCM), preference toggles, in-app notification history, and chat-triggered push delivery.

## Business Requirements

- Devices scoped to user + membership (multi-tenant aware)
- Preferences control push categories
- Chat messages create DB notification + optional push
- Auto-create preferences on new membership (signal)

## Models

| Model | Table | Notes |
|-------|-------|-------|
| `NotificationDevice` | `notification_devices` | FCM token, platform, `device_id` unique per membership |
| `NotificationPreference` | `notification_preferences` | Feature toggles |
| `Notification` | `notifications` | History; types: chat, mention, system, meeting |

## Architecture

```
NotificationService.create_notification (atomic)
  → PushService.send_push_notification
      → Celery push_tasks (async FCM)
          → FirebaseProvider
```

Firebase initialized via `integrations/firebase.py` and `FIREBASE_CREDENTIALS` env.

## Services

| Service | Responsibility |
|---------|----------------|
| `device_service` | Register/deactivate/list devices |
| `preference_service` | Get/update preferences |
| `notification_service` | Create notifications; `send_chat_notification`, `send_meeting_notification` |
| `push_service` | Resolve devices, build payload, enqueue send |

## Selectors

`notification_selectors.py` is **empty** — refactor opportunity.

## Serializers

`apps/notifications/api/v1/serializers.py` — device registration, preference fields.

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST devices/register/` | Register FCM token |
| `POST devices/deactivate/` | Deactivate device |
| `GET devices/` | List active devices |
| `GET/PATCH preferences/` | Notification preferences |

Requires authentication + company context (verify views inherit `BaseCompanyAPIView`).

## Permissions & Roles

No fine-grained notification permission codes — membership context sufficient.

## Realtime/WebSocket Flows

Push is complementary to WebSocket chat. No notification-specific WebSocket events.

## Validation Rules

- Unique `(membership, device_id)`
- Preferences default True for all toggles
- Push skipped when `push_enabled` or category flag false

## Security Considerations

- FCM tokens are secrets — HTTPS only
- Push payload must not leak cross-tenant data — include only IDs client can resolve with auth
- `firebase/service-account.json` must not be committed

## Scalability Concerns

- Celery queue for push bursts
- Device table growth — `cleanup_tasks` for stale devices
- No pagination API documented for `Notification` history list

## Future Improvements

- Notification inbox API (list/mark read)
- Implement mention and attendance notification senders
- Empty selectors module
- Web push vs native token handling
