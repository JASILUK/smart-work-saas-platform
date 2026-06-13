# SBMS / SmartBiz — Full Project Context & PRD

> **Purpose of this document:** Paste this entire file into any AI assistant so it understands the project accurately before writing code, designing features, or making architectural decisions.  
> **Scope:** Backend only — `SBMS_BACKEND` repository, primarily `services/api-service`.  
> **Last aligned to codebase:** June 2026.

---

## 1. PRODUCT OVERVIEW

### What is this?

**SmartBiz (SBMS)** is a **multi-tenant B2B SaaS platform** for organizations to manage:

- Company structure (departments, employees, invites)
- Role-based access control per company
- Real-time team chat (direct, group, department channels)
- Video meetings with LiveKit RTC
- Google Calendar sync for meetings
- Push notifications (FCM)
- Subscription/plan gating

The backend is a **microservice-oriented monorepo**:

| Service | Role | Maturity |
|---------|------|----------|
| `services/api-service` | Main Django API + WebSockets + Celery | **Production-building** |
| `services/ai-service` | FastAPI health stub | **Stub only** |
| `gateway/` | Nginx reverse proxy | **Implemented** |

### Product name in code

- `APP_NAME = "SmartBiz"` in Django settings
- Repo folder: `SBMS_BACKEND`

### Target users

1. **Tenant users** — employees/managers inside a company (most APIs)
2. **Platform staff** — internal admins (`core_platform` app — partially built)
3. **Clients** — web (cookie JWT) and mobile (Bearer JWT)

---

## 2. HIGH-LEVEL ARCHITECTURE

```
                    ┌─────────────┐
                    │   Browser   │
                    │  / Mobile   │
                    └──────┬──────┘
                           │ HTTP + WS
                    ┌──────▼──────┐
                    │   Gateway   │  nginx :8001
                    │  /api/ /ws/ │
                    └──────┬──────┘
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌───▼───┐ ┌─────▼─────┐
       │ api-service │ │  ai   │ │ postgres  │
       │ Daphne ASGI │ │ stub  │ │  redis    │
       │ Celery x2   │ └───────┘ └───────────┘
       └─────────────┘
```

### Infrastructure (`infrastructure/docker-compose.yml`)

| Container | Command | Notes |
|-----------|---------|-------|
| `gateway` | nginx | Port 8001 → routes `/api/`, `/ws/`, `/ai/` |
| `api` | `daphne config.asgi:application` | ASGI HTTP + WebSocket |
| `api-worker` | `celery -A config worker` | Async tasks |
| `api-beat` | `celery -A config beat` | Periodic tasks (DB scheduler) |
| `ai` | FastAPI uvicorn | Health only |
| `postgres-api` | PostgreSQL 15 | Single DB |
| `redis` | Redis 7 | Channels, Celery, cache, presence |

### Gateway routes (`gateway/nginx/nginx.conf`)

| Path | Upstream |
|------|----------|
| `/api/` | `api:8000` |
| `/ws/` | `api:8000` (WebSocket, 24h timeout) |
| `/admin/`, `/static/` | `api:8000` |
| `/ai/` | `ai:8000` |

---

## 3. TECH STACK (api-service)

| Layer | Technology |
|-------|------------|
| Framework | Django 4.2.28 |
| API | Django REST Framework |
| Auth | SimpleJWT + token blacklist |
| Realtime | Django Channels + Redis channel layer |
| ASGI server | Daphne |
| DB | PostgreSQL |
| Cache | django-redis (Redis DB 2) |
| Task queue | Celery (Redis DB 0 broker, DB 1 results) |
| Beat | django-celery-beat (DatabaseScheduler) |
| Media | Cloudinary |
| Push | Firebase Cloud Messaging |
| Video RTC | LiveKit |
| Calendar | Google Calendar API + OAuth |
| Email/SMS | Pluggable providers (console, SendGrid, Twilio) |

---

## 4. MULTI-TENANCY MODEL (CRITICAL)

### How tenancy works

- Each **Company** is a tenant.
- Users join companies via **Membership** (user + company + role + optional department).
- **All tenant APIs require header:** `X-Company-ID: <company_pk>`
- Server validates: authenticated user has active `Membership` for that company.
- Sets on request: `request.company`, `request.membership`, `request.subscription`

### Identity vs tenant actor

| Concept | Model | Used for |
|---------|-------|----------|
| Global login identity | `users.User` | Auth, MFA, OAuth |
| Tenant actor | `companies.Membership` | Chat messages, meetings, notifications, calendar |
| Chat WS identity | `membership.id` | NOT `user.id` |

**RULE FOR AI:** Never use `User.id` as chat/meeting sender. Always use `Membership.id`.

### Subscription gate

Every `BaseCompanyAPIView` endpoint also checks `ActiveSubscriptionPermission`:

- Blocks if subscription status is `expired` or `past_due`
- Sets `request.subscription`

---

## 5. ARCHITECTURAL PATTERNS (MUST FOLLOW)

### Service layer

```
View → Serializer (I/O) → Service (business logic) → Model
                       ↘ Selector (read queries)
```

- **Services** (`apps/*/services/`): writes, transactions, side effects
- **Selectors** (`selectors.py` or `selectors/`): read-optimized queries
- **Views**: thin — no business logic
- **Serializers**: validation + response shape only

### Transactions

Use `@transaction.atomic` on any service method that:

- Creates multiple related rows
- Updates + broadcasts
- Triggers Celery after DB write (prefer `on_commit`)

### Errors

Raise `apps.core.exceptions.ApplicationError("message")` for business failures.  
Global handler: `apps.core.exception_handler.custom_exception_handler`

### API responses

Use `success_response()` / `error_response()` from `apps.core.api_response`

### Tenant view base class

```python
from apps.companies.api.base import BaseCompanyAPIView

class MyAPI(BaseCompanyAPIView):
    required_permissions = {
        "GET": "tenant.something.view",
        "POST": "tenant.something.create",
    }
```

If HTTP method not in `required_permissions`, `RolePermission` allows any company member.

---

## 6. AUTHENTICATION

### HTTP

`UniversalJWTAuthentication` (`apps/users/authentication.py`):

1. Try HttpOnly cookie `access_token` (web)
2. Fallback to `Authorization: Bearer <token>` (mobile)

### JWT settings

- Access token: 15 minutes
- Refresh token: 7 days, rotated, blacklisted after rotation

### WebSocket

`apps/realtime/middlewares/websocket_auth.py`:

1. **Preferred:** `?ticket=<uuid>` — one-time ticket from `POST /api/chat/v1/ws-ticket/`
2. **Fallback:** `?token=<jwt>` + `tenant_id` query param for membership resolution

### Auth API base

`/api/users/v1/auth/*` — registration, login, MFA, OAuth, password reset, me

---

## 7. PERMISSIONS (RBAC)

### Model

- `rbac.Permission` — `code` (unique), `scope` (tenant | platform)
- `rbac.Role` — per company, M2M permissions
- Seeded via `python manage.py seed_permission`

### Tenant role blueprints (`apps/rbac/conf.py`)

| Role | Pattern |
|------|---------|
| Owner | `tenant.*` |
| Admin | company, employee, department, project, role.view, subscription.view |
| Manager | subset |
| Member | basic view access |

### Important permission codes

```
tenant.company.view / update
tenant.employee.create / view / update / delete / block
tenant.department.view / create / update / delete
tenant.meeting.create / view / update / cancel / start / join / invite / manage
tenant.attendance.view / manage
tenant.project.create / view / update / delete  ← NO PROJECTS APP YET
tenant.role.view / create / update / delete
tenant.subscription.view / update
platform.*  ← platform admin codes exist but platform API not mounted
```

### Known RBAC issues

- Typo: `tenent.employee.create` in one employee view (not in seed list)
- `api/platform/v1/` points to **tenant RBAC urls**, not `core_platform` urls
- Calendar views have **no** `required_permissions` declared
- Some meeting PATCH/DELETE rely on mixin checks, not always RBAC codes

---

## 8. ALL DJANGO APPS — STATUS & DETAIL

### 8.1 `apps.core`

Shared foundation. No HTTP API.

- `TimeStampedModel` — base for most models
- `api_response.py`, `exception_handler.py`, `media_storage_service.py`

### 8.2 `apps.users` ✅ IMPLEMENTED

**Models:** `User`, `MFADevice`, `BackupCode`, `SocialAccount`, `VerificationToken`

**API:** `/api/users/v1/`

**Features:** Register, register-with-company, email verify, login, MFA, Google OAuth, password reset, me, refresh, logout

### 8.3 `apps.companies` ✅ IMPLEMENTED

**Models:** `Company`, `Department`, `Membership`, `CompanyInvite`

**API:** `/api/company/v1/`

**Features:**
- Company context API
- Employee list/detail/block/unblock
- Department CRUD + member assign/remove/transfer
- Invites: single, bulk, CSV
- Department has `conversation` OneToOne → auto department chat

### 8.4 `apps.rbac` ✅ IMPLEMENTED

**Models:** `Permission`, `Role`

**API:** `/api/rbac/v1/` (also wrongly mounted at `/api/platform/v1/`)

**Features:** Role CRUD, permission list

### 8.5 `apps.billing` ⚠️ PARTIAL

**Models:** `Plan`, `Subscription`

**API:** `/api/billing/v1/plans/` — list plans only

**Features:**
- Subscription created on company registration
- `ActiveSubscriptionPermission` gates tenant APIs
- Plan flags: `automation_enabled`, `ai_credits_per_month`, `max_users`, etc.
- **No Stripe/payment webhooks implemented**

### 8.6 `apps.chat` ✅ IMPLEMENTED

**Models:** `Conversation`, `ConversationParticipant`, `Message`, `MessageStatus`

**Conversation types:** direct, group, department, project (project type has no Project model)

**API:** `/api/chat/v1/`

**Features:**
- DM, group, department chat
- Text + media messages (Cloudinary)
- Reply, edit, soft delete
- Read receipts (sent → delivered → read)
- Unread counts per participant
- System messages for group events
- WS ticket endpoint

**Realtime:** Handled via `apps/realtime` + `ChatRealtimeHandler`

### 8.7 `apps.notifications` ✅ IMPLEMENTED

**Models:** `NotificationDevice`, `NotificationPreference`, `Notification`

**API:** `/api/notification/v1/`

**Features:**
- FCM device register/deactivate/list
- Per-membership preferences (chat, meeting, attendance, mention, system)
- Chat + meeting push notifications
- Celery async push delivery
- Signal: auto-create preferences on new membership

**Missing:** Notification inbox list/mark-read REST API

### 8.8 `apps.meetings` ✅ IMPLEMENTED

**Models:**

| Model | Purpose |
|-------|---------|
| `Meeting` | Core meeting; `public_id` UUID; category, visibility, schedule type, status, recurrence |
| `MeetingTarget` | Target audience: department, project, team |
| `MeetingSession` | RTC session; LiveKit room; status waiting/live/ended |
| `MeetingParticipant` | Roles, invite status, **attendance tracking** |

**API:** `/api/meetings/v1/`

| Endpoint | Methods |
|----------|---------|
| `""` | GET list, POST create |
| `<public_id>/` | GET, PATCH, DELETE |
| `<public_id>/targets/` | GET, POST |
| `<public_id>/targets/<id>/` | PATCH, DELETE |
| `<public_id>/participants/` | GET, POST |
| `<public_id>/participants/<id>/` | PATCH, DELETE |
| `<public_id>/session/` | GET session detail |
| `<public_id>/session/start/` | POST start (LiveKit room) |
| `<public_id>/session/end/` | POST end |
| `<public_id>/session/join/` | POST join (returns RTC token) |
| `<public_id>/session/leave/` | POST leave |

**Services:**
- `MeetingService` — CRUD; triggers calendar sync + reminders on commit
- `MeetingSessionService` — start/join/leave/end; LiveKit integration
- `MeetingAttendanceService` — join/leave tracking, duration, percentage, finalize
- `MeetingReminderService` — creates reminders via reminders app
- `RecurrenceService`, `SchedulingService`, `RTCEventService`

**RTC:** LiveKit only (factory). Settings: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`

**Attendance:** Implemented in services + WebSocket (`join_meeting`/`leave_meeting`). **No REST attendance API** (`attendance_views.py` is empty stub).

**Missing:** `LiveKitWebhookAPI` exists but **not registered in urls**

### 8.9 `apps.calendars` ✅ IMPLEMENTED (Google only)

**Models:**
- `CalendarAccount` — per membership; Google/Outlook enum; OAuth tokens
- `CalendarEventSync` — links internal object to external calendar event

**API:** `/api/calendars/v1/`

| Endpoint | Purpose |
|----------|---------|
| `accounts/` | List connected calendars |
| `connect-url/` | Get OAuth URL (`?provider=google`) |
| `callback/` | OAuth callback |
| `disconnect/` | Disconnect account |

**Google integration:** `apps/calendars/integrations/google/` — OAuth, Calendar API CRUD

**Sync flow:** Meeting create/update/cancel → `CalendarRegistrationService` → Celery `sync_calendar_event` / `delete_calendar_event`

**Missing:** Outlook not implemented; `refresh_token_tasks.py` is empty

### 8.10 `apps.reminders` ⚠️ PARTIAL (backend only)

**Model:** `Reminder` — target types: meeting, payroll, attendance, project, task, invoice, subscription

**Services:** `ReminderService`, `MeetingReminderHandler`

**Celery:** `process_due_reminders` — **only handles `TargetType.MEETING`**

**Integration:** `MeetingReminderService` creates reminders (default: 1440, 60, 15 min before)

**Missing:**
- No HTTP API (`urls.py` empty, not in root urls)
- Celery beat schedule not seeded in code
- Other target types raise `ValueError` if processed

### 8.11 `apps.core_platform` ⚠️ WRITTEN, NOT MOUNTED

**Models:** `PlatformRole`, `PlatformProfile`

**API exists** at `apps/core_platform/api/v1/urls.py` but **NOT in `config/urls.py`**

Platform WebSocket consumer exists at `ws/platform/`

### 8.12 `apps.realtime` — NOT a Django app

WebSocket layer (in `INSTALLED_APPS`? **NO** — just a package)

**Routing:** `apps/realtime/routing.py`

| WS Path | Consumer |
|---------|----------|
| `ws/app/` | `TenantConsumer` |
| `ws/platform/` | `PlatformConsumer` |

**TenantConsumer handles:**
- Chat (via `ChatRealtimeHandler`)
- Meetings presence + attendance (via `MeetingRealtimeHandler`)
- Meeting chat (via `MeetingChatRealtimeHandler`)
- Tenant presence (Redis online sets)
- Typing, read receipts, delivery ACKs

**Unwired dead code:** `chat_consumer.py`, `presence_consumer.py`, `main_consumer.py`

---

## 9. WEBSOCKET PROTOCOL SUMMARY

### Connect

```
wss://host/ws/app/?ticket=<one-time-uuid>
```

Get ticket: `POST /api/chat/v1/ws-ticket/` with `X-Company-ID`

### Channel groups

| Pattern | Purpose |
|---------|---------|
| `tenant_{company_id}_user_{membership_id}` | Personal events, sidebar |
| `tenant_{company_id}` | Tenant-wide presence |
| `tenant_{company_id}_room_{conversation_id}` | Chat room |
| `tenant_{company_id}_meeting_{meeting_public_id}` | Meeting presence |

### Client → Server events

| type | Purpose |
|------|---------|
| `join_room` | Join chat conversation |
| `leave_room` | Leave chat conversation |
| `message_received` | Delivery ACK |
| `mark_read` | Mark room read |
| `typing_start` / `typing_stop` | Typing indicator |
| `join_meeting` / `leave_meeting` | Meeting presence + attendance |
| `meeting_message` | Meeting chat message |
| `meeting_typing` | Meeting chat typing |

### Known WS security gap

`join_room` does **not** verify `ConversationParticipant` — must be fixed before production.

---

## 10. EXTERNAL INTEGRATIONS

| Integration | Location | Status |
|-------------|----------|--------|
| Google OAuth (login) | `integrations/Oauth/google.py` | ✅ |
| Google Calendar OAuth | `apps/calendars/integrations/google/` | ✅ |
| GitHub OAuth | `integrations/Oauth/github.py` | File exists |
| Firebase FCM | `integrations/firebase.py` + notifications providers | ✅ |
| Cloudinary | `apps/core/media_storage_service.py` | ✅ |
| LiveKit | `apps/meetings/integrations/rtc/livekit/` | ✅ |
| Email/SMS | `integrations/notifications.py` | ✅ (pluggable) |
| Stripe/payments | Subscription model fields only | ❌ |

---

## 11. CELERY TASKS

| Task | App | Purpose |
|------|-----|---------|
| `send_invite_email_task` | companies | Invite emails |
| `send_notification_task` | users | Generic notifications |
| `push_tasks` | notifications | FCM delivery |
| `cleanup_tasks` | notifications | Device cleanup |
| `sync_calendar_event` | calendars | Push event to Google |
| `delete_calendar_event` | calendars | Remove from Google |
| `process_due_reminders` | reminders | Send meeting reminders |
| `auto_end_empty_meeting_task` | meetings | Auto-end empty sessions |

Beat uses `DatabaseScheduler` — schedules must be configured in Django admin or DB.

---

## 12. COMPLETE API MAP

```
POST/GET  /api/users/v1/auth/*          → users
GET       /api/billing/v1/plans/        → billing
GET/POST  /api/company/v1/*             → companies
GET/POST  /api/rbac/v1/*                → rbac
GET/POST  /api/platform/v1/*            → rbac (WRONG — should be core_platform)
GET/POST  /api/chat/v1/*                → chat
GET/POST  /api/notification/v1/*        → notifications
GET/POST  /api/meetings/v1/*            → meetings
GET/POST  /api/calendars/v1/*           → calendars

NOT MOUNTED:
  /api/reminders/v1/                    → reminders (empty urls)
  /api/platform/v1/ (core_platform)     → platform admin
```

---

## 13. FEATURE MATRIX — IMPLEMENTED vs MISSING

| Feature | Status | Notes |
|---------|--------|-------|
| User auth + MFA + OAuth | ✅ | |
| Multi-tenant companies | ✅ | |
| Departments + dept chat | ✅ | |
| Employee management + invites | ✅ | |
| RBAC per company | ✅ | |
| Subscription gating | ✅ | No payment integration |
| Real-time chat | ✅ | |
| Push notifications | ✅ | No inbox API |
| Video meetings (LiveKit) | ✅ | Webhook not routed |
| Meeting attendance (in-meeting) | ⚠️ | Service + WS only, no REST |
| Google Calendar sync | ✅ | Google only |
| Meeting reminders | ⚠️ | Backend only, needs beat schedule |
| Platform admin API | ❌ | Code exists, not mounted |
| Projects module | ❌ | Permission codes + enum only |
| Teams module | ❌ | Enum only |
| HR attendance (clock in/out) | ❌ | Preference field only |
| Automations engine | ❌ | Plan flag only |
| AI agents / LLM | ❌ | ai-service is health stub |
| Outlook calendar | ❌ | Enum only |
| Stripe billing | ❌ | Model fields only |
| Workflow engine | ❌ | Comments in dept service ≠ product feature |

---

## 14. KNOWN BUGS & PITFALLS (AI MUST NOT REPEAT)

1. **Do not assume meetings is unbuilt** — it is fully implemented with LiveKit
2. **Do not put WebSocket consumers in `apps/chat`** — they live in `apps/realtime`
3. **Do not use `apps/chat/routing.py`** — use `apps/realtime/routing.py`
4. **Do not use `User.id` for chat/meeting** — use `Membership.id`
5. **Do not mount platform APIs to rbac urls** — use `core_platform.api.v1.urls`
6. **Do not create a `projects` app without explicit request** — only stubs exist
7. **`Conversation.Type.PROJECT` exists** but no Project model — do not build project chat without Project model
8. **`MeetingTarget.TargetType.PROJECT`** validates with `pass` — no FK check
9. **WS `join_room` lacks participant check** — security gap
10. **`leave_session` HTTP does not call attendance service** — only WS `leave_meeting` does
11. **Typo filenames exist** — `tanent_consumer.py`, `emplyee_service.py` — match existing names when editing
12. **`DEBUG=True` in base settings** — production must use `config.settings.production`
13. **Firebase credentials file** may be in repo — never commit secrets
14. **Reminders app has no HTTP API** — do not document endpoints that don't exist
15. **docs/features/meetings.md may be outdated** — trust this document and source code

---

## 15. RULES FOR AI WHEN BUILDING NEW FEATURES

### Always

- [ ] Use `BaseCompanyAPIView` for tenant endpoints
- [ ] Require `X-Company-ID` header
- [ ] Put business logic in `services/`, queries in `selectors/`
- [ ] Use `@transaction.atomic` for multi-step writes
- [ ] Raise `ApplicationError` for business failures
- [ ] Return `success_response` / `error_response`
- [ ] Declare `required_permissions` per HTTP method
- [ ] Add permission codes to `seed_permission.py` if new
- [ ] Use `Membership` as actor in tenant-scoped features
- [ ] Register new urls in `config/urls.py`
- [ ] Add migrations for model changes
- [ ] Use `TimeStampedModel` for new models
- [ ] Broadcast realtime via `channel_layer.group_send` from services
- [ ] Enqueue Celery tasks with `transaction.on_commit` when needed

### Never

- [ ] Put business logic in views or serializers
- [ ] Create duplicate WebSocket routing files
- [ ] Assume `api/platform/v1/` is platform admin API
- [ ] Assume projects/teams/automations/AI exist as apps
- [ ] Use sync ORM directly inside async consumers (use `database_sync_to_async`)
- [ ] Skip subscription permission check on tenant APIs
- [ ] Invent API endpoints not registered in urls.py

### When adding meetings/calendar features

- Hook calendar sync via `CalendarRegistrationService`
- Hook reminders via `MeetingReminderService` / `ReminderService`
- Use `public_id` (UUID) in meeting URLs, not integer PK
- LiveKit tokens via `MeetingSessionService`
- Attendance via `MeetingAttendanceService`

### When adding realtime

- Extend handlers in `apps/chat/realtime/` or `apps/meetings/realtime/`
- Wire through `TenantConsumer` dispatch
- Use group naming: `tenant_{id}_...`
- Prefer ticket auth over JWT in query strings

---

## 16. ENVIRONMENT VARIABLES

```env
# Core
SECRET_KEY=
DJANGO_ENV=local|production
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
DB_HOST=
DB_PORT=
REDIS_URL=

# Auth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_CALENDAR_REDIRECT_URI=
FRONTEND_URL=

# Media
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Push
FIREBASE_CREDENTIALS=

# RTC
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=

# Email
EMAIL_PROVIDER=console|sendgrid|smtp
EMAIL_HOST=
EMAIL_PORT=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=

# SMS
SMS_PROVIDER=console|twilio
```

---

## 17. REPOSITORY STRUCTURE

```
SBMS_BACKEND/
├── gateway/
│   ├── Dockerfile
│   └── nginx/nginx.conf
├── infrastructure/
│   └── docker-compose.yml
└── services/
    ├── api-service/
    │   ├── config/
    │   │   ├── settings/base.py
    │   │   ├── urls.py
    │   │   ├── asgi.py
    │   │   └── celery.py
    │   ├── apps/
    │   │   ├── core/
    │   │   ├── users/
    │   │   ├── companies/
    │   │   ├── rbac/
    │   │   ├── billing/
    │   │   ├── chat/
    │   │   ├── notifications/
    │   │   ├── meetings/
    │   │   ├── calendars/
    │   │   ├── reminders/
    │   │   ├── core_platform/
    │   │   └── realtime/          ← WebSocket (not INSTALLED_APP)
    │   ├── integrations/
    │   ├── templates/
    │   └── docs/
    └── ai-service/
        └── main.py                 ← health stub only
```

---

## 18. PRODUCT REQUIREMENTS (PRD SUMMARY)

### P0 — Shipped / shipping

| Requirement | Acceptance criteria |
|-------------|---------------------|
| User can register and login | Email verify, JWT, MFA optional |
| User can create/join company | Membership + role assigned |
| Admin can invite employees | Email invite, bulk, CSV |
| Admin can manage departments | CRUD + linked dept chat |
| Users can chat in real-time | DM, group, dept; WS + HTTP |
| Users receive push notifications | FCM register + chat/meeting push |
| Users can schedule and run meetings | CRUD, LiveKit join, session lifecycle |
| Meetings sync to Google Calendar | OAuth connect + event sync |
| Meeting reminders fire | Celery task (needs beat config) |
| Plans gate access | Subscription status check |

### P1 — Partial / needs completion

| Requirement | Gap |
|-------------|-----|
| Meeting attendance reporting | No REST API; finalize on session end only |
| LiveKit webhooks | View exists, not routed |
| Platform admin | API not mounted |
| Notification inbox | No list/mark-read API |
| Outlook calendar | Not implemented |
| Payment / upgrade | No Stripe |
| Plan limit enforcement | max_users etc. not enforced everywhere |
| Reminder beat schedule | Not seeded |

### P2 — Not started

| Requirement | Notes |
|-------------|-------|
| Projects module | Codes seeded only |
| Teams module | Enum only |
| HR attendance | Not meeting attendance |
| Automations | Plan flag only |
| AI agents | ai-service stub |
| Workflow engine | N/A |

---

## 19. GLOSSARY

| Term | Meaning |
|------|---------|
| Tenant | A `Company` |
| Membership | User's role inside a company |
| Actor | The `Membership` performing an action |
| public_id | External UUID for meetings (not integer PK) |
| Ticket | One-time WS auth token in Redis cache |
| System-managed conversation | Auto-created chat (e.g. department) — limited user control |
| Target (meeting) | Audience scope: department, project, or team |
| RTC | Real-time communication — LiveKit video/audio |

---

## 20. QUICK REFERENCE FOR AI PROMPTS

When asking an AI to work on this project, include:

```
You are working on SmartBiz (SBMS) backend.
Stack: Django 4.2 + DRF + Channels + Celery + PostgreSQL + Redis.
Multi-tenant via X-Company-ID header and Membership model.
Follow service/selector pattern. Use BaseCompanyAPIView for tenant APIs.
WebSockets are in apps/realtime, not apps/chat.
Meetings + calendars + chat are implemented. Projects/AI/automations are NOT.
Read PROJECT_CONTEXT.md before making changes.
```

---

*End of document. For deeper module docs see `services/api-service/docs/` directory.*
