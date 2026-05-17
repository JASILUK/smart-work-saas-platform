# Notifications API

Base path: `/api/notification/v1/`

**Required:** Authentication + company context (membership-scoped devices).

## Devices

| Method | Path | Purpose |
|--------|------|---------|
| POST | `devices/register/` | Register FCM token + `device_id`, `platform` |
| POST | `devices/deactivate/` | Deactivate by device_id |
| GET | `devices/` | List membership's devices |

### Register payload (typical)

- `device_id` — client-generated stable ID
- `token` — FCM registration token
- `platform` — `web` | `android` | `ios`
- `device_name` — optional label

## Preferences

| Method | Path | Purpose |
|--------|------|---------|
| GET | `preferences/` | Get `NotificationPreference` for membership |
| PATCH | `preferences/` | Update toggles |

### Preference fields

- `push_enabled`, `sound_enabled`
- `chat_message_enabled`, `mention_enabled`
- `meeting_enabled`, `attendance_enabled`, `system_enabled`

## Missing APIs

| Capability | Status |
|------------|--------|
| List in-app `Notification` history | No route in urls.py |
| Mark notification read | Not exposed |

Implement in `apps/notifications/api/v1/urls.py` when product requires inbox UI.

## Related

- [../features/notifications.md](../features/notifications.md)
- [../websocket/notification-events.md](../websocket/notification-events.md)
