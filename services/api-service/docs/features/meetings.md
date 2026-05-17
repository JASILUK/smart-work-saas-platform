# Meetings

## Status: **Not Implemented**

There is no `meetings` Django app, no meeting models, and no meeting HTTP API in this service.

## What Exists Today (Stubs Only)

| Artifact | Location |
|----------|----------|
| `NotificationPreference.meeting_enabled` | `apps/notifications/models.py` |
| `Notification.Type.MEETING` | notifications model |
| `NotificationService.send_meeting_notification()` | `apps/notifications/services/notification_service.py` |

These support **future** push/in-app notifications when a meetings feature is built elsewhere or added here.

## Purpose (Intended)

When implemented, meetings would likely require:

- `Meeting` model (company, organizer membership, schedule, participants)
- Calendar integration or internal scheduling
- RBAC codes (not yet in active seed beyond notification prefs)
- Realtime reminders via notifications + optional WS events

## Business Requirements

**Not defined in codebase.** Product requirements must be specified before implementation.

## Architecture Recommendation

- New app `apps.meetings` or service-owned module in a future PR
- Reuse `NotificationService.send_meeting_notification`
- Tenant scoping via `BaseCompanyAPIView`
- Do not overload `chat.Conversation` for meetings unless explicitly designed

## Security / Scalability

N/A until implemented.

## Future Improvements

1. Add domain models and migrations
2. CRUD + participant APIs under `/api/meetings/v1/`
3. Wire notification sender on create/reminder
4. Add RBAC permission codes to `seed_permission`
5. Document in [../api/meetings-api.md](../api/meetings-api.md) when built
