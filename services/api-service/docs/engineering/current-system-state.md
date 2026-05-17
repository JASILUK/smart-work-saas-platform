# Current System State

Snapshot of the API service as implemented in repository. Last aligned to codebase structure under `services/api-service`.

## Production-Ready Features

| Feature | Maturity | Notes |
|---------|----------|-------|
| User auth + JWT + MFA | High | Cookie + Bearer |
| Company + membership | High | Invites, bulk CSV |
| Departments + dept chat | Medium-High | Conversation linked |
| RBAC roles/permissions | Medium | Seeded; custom roles flag on plan |
| Billing plans + subscription gate | Medium | List plans only; no Stripe API |
| Chat DM/group/dept | High | WS + HTTP |
| Push notifications (FCM) | Medium | Device + prefs; limited inbox API |
| Platform roles model | Low | APIs not mounted |

## Partial / Stub Features

| Feature | State |
|---------|-------|
| Meetings | Preference + `send_meeting_notification` only |
| Attendance | Preference field only |
| AI credits | Plan field only |
| Automations | Plan flag only |
| Project conversations | Enum only, no Project model |
| Platform admin API | Written but not in root urls |
| GitHub OAuth | Integration file exists; verify exposed in urls |

## Active WebSocket Routes

- `ws/app/` → `TenantConsumer`
- `ws/platform/` → `PlatformConsumer`

## Dead / Unwired Code

- `chat_consumer.py`, `presence_consumer.py`, `main_consumer.py`
- `core_platform/api/v1/urls.py` not included in `config/urls.py`
- `notification_selectors.py` empty
- `PLATFORM_ROLE_BLUEPRINTS = {}`

## Infrastructure Dependencies

| Service | Required |
|---------|----------|
| PostgreSQL | Yes |
| Redis | Yes (Channels, Celery, cache, presence) |
| Cloudinary | Media uploads |
| Firebase | Push (optional if push disabled) |
| SMTP/SendGrid | Email |
| Celery worker | Invites, push |

## Git Status Notes (Recent Work)

Per branch state: active development on departments, chat system messages, notifications app, Firebase integration. Migrations pending apply in deploy environments.

## API Surface Summary

| Prefix | Active |
|--------|--------|
| `/api/users/v1/` | Yes |
| `/api/company/v1/` | Yes |
| `/api/rbac/v1/` | Yes |
| `/api/platform/v1/` | Yes (duplicate rbac) |
| `/api/billing/v1/` | Yes |
| `/api/chat/v1/` | Yes |
| `/api/notification/v1/` | Yes |
| `/api/platform/v1/` (core_platform) | No |

## Related

- [known-issues.md](./known-issues.md)
- [future-roadmap.md](./future-roadmap.md)
