# Known Issues

Factual issues identified from code review. Severity for production operations.

## Critical / High

| ID | Issue | Risk |
|----|-------|------|
| KI-001 | WebSocket `join_room` does not verify `ConversationParticipant` | Unauthorized subscription to conversation events |
| KI-002 | `firebase/service-account.json` may be committed | Credential leak |
| KI-003 | `DEBUG = True` in `base.py` | Information disclosure if production uses base without override |
| KI-004 | `api/platform/v1/` includes rbac urls, not `core_platform` | Platform admin non-functional / wrong API |

## Medium

| ID | Issue | Risk |
|----|-------|------|
| KI-005 | JWT WS fallback without `tenant_id` | Connection without membership |
| KI-006 | `mark_all_as_delivered_on_connect` loads all SENT rows | Slow connect for heavy users |
| KI-007 | No HTTP rate limiting | Abuse of auth/chat/invite |
| KI-008 | Plan limits (`max_users`, etc.) not enforced everywhere | Billing bypass |
| KI-009 | `Conversation.Type.PROJECT` without Project domain | Broken client assumptions |
| KI-010 | Unwired WebSocket consumers | Maintainer confusion |
| KI-011 | No health check endpoint | Orchestration blind spots |
| KI-012 | `print()` in WS consumers | No structured observability |

## Low

| ID | Issue | Risk |
|----|-------|------|
| KI-013 | Filename typos (`tanent`, `emplyee`, `Serailzer`) | Onboarding friction |
| KI-014 | Duplicate `MessageService` modules | Import confusion |
| KI-015 | Empty `notification_selectors.py` | Query duplication |
| KI-016 | No notification history API | Incomplete product |
| KI-017 | `RolePermission` allows access when permission key missing for method | Accidental open endpoints |
| KI-018 | Room group not left on disconnect | Stale channel group membership until leave |

## Configuration

| ID | Issue |
|----|-------|
| KI-019 | `CORS_ALLOWED_ORIGINS` localhost only in base |
| KI-020 | `CSRF_COOKIE_SECURE` / `SESSION_COOKIE_SECURE` false in base |
| KI-021 | No `CELERY_BEAT_SCHEDULE` for cleanup tasks |

## Remediation Priority

1. KI-001, KI-002, KI-003, KI-004
2. KI-005, KI-006, KI-007, KI-008
3. Remaining as backlog

## Related

- [../security-considerations.md](../security-considerations.md)
- [future-roadmap.md](./future-roadmap.md)
