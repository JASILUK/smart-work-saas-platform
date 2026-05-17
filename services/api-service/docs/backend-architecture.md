# Backend Architecture — SBMS API Service

## Overview

The **SBMS API Service** (`services/api-service`) is a Django 4.2 monolith exposing REST APIs and WebSocket realtime channels for a multi-tenant SaaS platform. It runs behind a gateway in a larger microservice topology but owns its own PostgreSQL schema, Redis usage, and ASGI process.

| Layer | Technology |
|-------|------------|
| HTTP | Django + Django REST Framework |
| Realtime | Django Channels + Redis channel layer |
| Auth | SimpleJWT (cookie + Bearer), WebSocket ticket/JWT |
| DB | PostgreSQL |
| Cache / tickets / presence | Redis (django-redis DB 2, raw redis client in chat) |
| Async jobs | Celery + Redis broker (DB 0/1) |
| Media | Cloudinary (`apps.core.media_storage_service`) |
| Push | Firebase Cloud Messaging (`apps.notifications`) |

## Installed Applications

| App | Responsibility |
|-----|----------------|
| `apps.core` | `TimeStampedModel`, API response envelope, global exception handler, media upload |
| `apps.users` | Identity, JWT sessions, MFA, OAuth, verification tokens |
| `apps.companies` | Tenants (`Company`), `Membership`, `Department`, invites |
| `apps.rbac` | Tenant-scoped `Permission` catalog and `Role` per company |
| `apps.billing` | `Plan` feature flags, `Subscription` gate for tenant APIs |
| `apps.chat` | Conversations, messages, read receipts, WebSocket consumers |
| `apps.core_platform` | Platform staff roles (`PlatformRole`, `PlatformProfile`) — **API not mounted in root URLs** |
| `apps.notifications` | FCM devices, preferences, in-app notification history, Celery push |

**Not present as Django apps:** meetings, attendance, workflows, AI agents, automations (only plan/preference stubs).

## Request Flow (HTTP)

```
Client
  → CORS (corsheaders, first in stack)
  → Security / WhiteNoise / Session / CSRF
  → AuthenticationMiddleware
  → DRF View
       → UniversalJWTAuthentication (cookie access_token, else Authorization: Bearer)
       → Default: IsAuthenticated
       → [Tenant APIs] BaseCompanyAPIView stack:
            CompanyContextPermission (X-Company-ID → request.company, request.membership)
            ActiveSubscriptionPermission
            RolePermission (view.required_permissions[method])
```

## Tenant Context Model

Multi-tenancy is **header-scoped**, not subdomain-scoped:

- Clients send `X-Company-ID` on tenant APIs.
- `CompanyContextPermission` resolves an active `Membership` with `select_related("company", "role")` and `prefetch_related("role__permissions")`.
- All company-scoped business logic should use `request.membership` (membership ID is the chat actor ID).

## Service-Layer Architecture

Business logic lives in `apps/*/services/`, not in views or serializers:

| Concern | Location |
|---------|----------|
| Orchestration, transactions, side effects | `*Service.py` / `*_service.py` |
| Read-optimized queries | `selectors.py` or `selectors/` |
| HTTP I/O | `api/v1/views.py` |
| Input/output shaping | `api/v1/serializers.py` |
| Cross-cutting errors | `apps.core.exceptions.ApplicationError` → `custom_exception_handler` |

Views are thin: validate input → call service → return `success_response` / `error_response` from `apps.core.api_response`.

## Realtime Architecture

- **ASGI entry:** `config.asgi.application`
- **WebSocket routes:** `apps.chat.routing` — only `TenantConsumer` (`ws/app/`) and `PlatformConsumer` (`ws/platform/`) are wired.
- **Auth:** `WebSocketAuthMiddleware` — one-time Redis cache ticket (preferred) or JWT query param; tenant WS requires `membership` for `tenant_id`.
- **Broadcasts:** `channels.layers` group names + direct Redis sets for presence/room activity.

Additional consumer modules (`chat_consumer.py`, `presence_consumer.py`, `main_consumer.py`) exist but are **not registered** in routing.

## Integrations (`integrations/`)

| Module | Role |
|--------|------|
| `Oauth/google.py` | Google ID token verification |
| `Oauth/github.py` | GitHub token → user profile |
| `firebase.py` | Firebase Admin SDK init from `FIREBASE_CREDENTIALS` |
| `notifications.py` | Pluggable email/SMS providers (console, SendGrid, Twilio) |
| `template_service.py` | Email/SMS template rendering |
| `auth_engines.py` | JWT helper utilities |

## URL Map (Root)

| Prefix | Module |
|--------|--------|
| `/admin/` | Django admin |
| `/api/users/v1/` | `apps.users.api.v1.urls` |
| `/api/billing/v1/` | `apps.billing.api.v1.urls` |
| `/api/company/v1/` | `apps.companies.api.v1.urls` |
| `/api/rbac/v1/` | `apps.rbac.api.v1.urls` |
| `/api/platform/v1/` | **Same as rbac** (`apps.rbac.api.v1.urls`) — not `core_platform` |
| `/api/chat/v1/` | `apps.chat.api.v1.urls` |
| `/api/notification/v1/` | `apps.notifications.api.v1.urls` |

**Gap:** `apps.core_platform.api.v1.urls` is defined but not included in `config/urls.py`.

## Cross-Cutting Concerns

### Exceptions

`REST_FRAMEWORK["EXCEPTION_HANDLER"]` = `apps.core.exception_handler.custom_exception_handler` — normalizes API error shape for clients.

### Celery

- App: `config.celery`
- Broker/backend: Redis DB 0 and 1
- `django_celery_beat` installed; no `CELERY_BEAT_SCHEDULE` in base settings
- Tasks: user notifications, company invite emails, notification push/cleanup

### Caching

`CACHES["default"]` → Redis DB 2 (isolated from Celery). Used for WebSocket tickets (`ws_ticket_{uuid}`).

## Architectural Strengths

- Clear separation: services vs selectors vs views
- Tenant APIs consistently use `BaseCompanyAPIView` permission stack
- Chat uses membership-scoped IDs (correct for multi-membership users)
- WebSocket ticket pattern avoids long-lived JWT in query strings
- Atomic message send with status rows and channel broadcast

## Known Structural Risks

| Risk | Impact |
|------|--------|
| `api/platform/v1/` points to tenant RBAC, not platform admin APIs | Platform management broken or misleading |
| Unwired WebSocket consumers | Dead code / confusion |
| `Conversation.Type.PROJECT` without Project model | Incomplete domain |
| Meetings/attendance/automation only as flags | Product docs must not overstate capabilities |
| `DEBUG = True` in `base.py` | Production must override via `config.settings.production` |
| `firebase/service-account.json` in tree | Credential leak risk — must not ship to production repos |

## Related Documents

- [database-architecture.md](./database-architecture.md)
- [websocket-architecture.md](./websocket-architecture.md)
- [service-layer-patterns.md](./service-layer-patterns.md)
- [permissions-system.md](./permissions-system.md)
