# Attendance

## Status: **Not Implemented**

No attendance models, services, selectors, APIs, or notification senders exist.

## What Exists Today (Stub Only)

| Artifact | Location |
|----------|----------|
| `NotificationPreference.attendance_enabled` | `apps/notifications/models.py` |
| Serializer field exposure | `apps/notifications/api/v1/serializers.py` |

No `Notification.Type.ATTENDANCE` or `send_attendance_notification` method.

## Purpose (Intended)

Typical attendance module would track check-in/out, shifts, or daily status per `Membership`, with manager reporting and push alerts.

## Business Requirements

**Undefined in code.**

## Architecture Recommendation

- App `apps.attendance` with company-scoped records
- FK to `Membership` and date/time fields
- Celery for reminder notifications respecting `attendance_enabled` preference
- RBAC: `tenant.attendance.*` permission family

## Future Improvements

1. Define attendance domain model
2. Implement APIs and enforce plan limits if applicable
3. Add notification type and sender symmetric to chat/meeting
4. Consider integration with meetings (optional)
