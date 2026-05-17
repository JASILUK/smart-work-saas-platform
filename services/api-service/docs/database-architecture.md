# Database Architecture

## Engine & Configuration

- **Engine:** PostgreSQL (`django.db.backends.postgresql`)
- **Connection:** env vars `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DB_HOST`, `DB_PORT`
- **Primary keys:** `BigAutoField` default; chat/notifications use UUID PKs where noted
- **Timestamps:** Most models inherit `TimeStampedModel` (`created_at`, `updated_at`)

## Entity Relationship Overview

```
User ──┬── Membership ──┬── Company
       │                ├── Role (M2M Permission)
       │                ├── Department (optional FK)
       │                └── NotificationPreference (1:1)
       │
       ├── SocialAccount, MFADevice, BackupCode, VerificationToken
       ├── NotificationDevice (also FK membership)
       └── PlatformProfile → PlatformRole (M2M Permission)

Company ──┬── Subscription → Plan (1:1 company)
          ├── Department ──┬── head → Membership
          │                └── conversation → Conversation (1:1, system-managed)
          ├── Membership
          ├── CompanyInvite
          └── Conversation (many)

Conversation ──┬── ConversationParticipant → Membership
               ├── Message → MessageStatus (per membership)
               └── last_message → Message (nullable FK)

Notification → Membership
```

## Schema by Domain

### Identity (`users`)

| Model | Key constraints |
|-------|-----------------|
| `User` | `email` unique; `USERNAME_FIELD=email`; `active_company` nullable FK |
| `MFADevice` | Per-user TOTP/SMS devices |
| `BackupCode` | One-time MFA recovery |
| `SocialAccount` | `unique_together (provider, provider_account_id)` |
| `VerificationToken` | Typed tokens with `expires_at`, `is_used` |

### Tenancy (`companies`)

| Model | Key constraints |
|-------|-----------------|
| `Company` | `slug` unique; `status` pending/active/suspended; `owner` PROTECT |
| `Department` | `unique_together (company, name)`; tree via `parent`; `conversation` OneToOne nullable |
| `Membership` | `unique_together (user, company)`; `role` PROTECT; `department` optional |
| `CompanyInvite` | `token_id` UUID unique; `token_hash`; expiry |

**Indexes:** company slug/status; membership company/department/is_active; department company/parent/head.

### RBAC (`rbac`)

| Model | Notes |
|-------|-------|
| `Permission` | `code` unique; `scope` platform \| tenant |
| `Role` | Per-company; M2M permissions; `is_system_role` |

Seeded via `management/commands/seed_permission.py` from `TENANT_ROLE_BLUEPRINTS` patterns.

### Billing (`billing`)

| Model | Notes |
|-------|-------|
| `Plan` | Feature flags: `automation_enabled`, `custom_roles_enabled`, limits (`max_users`, `ai_credits_per_month`, etc.) |
| `Subscription` | OneToOne `Company`; status enum; provider fields for future payment integration |

### Chat (`chat`)

| Model | Notes |
|-------|-------|
| `Conversation` | UUID PK; `type` direct/group/department/project; `is_system_managed`; `company` FK |
| `ConversationParticipant` | `unique_together (conversation, membership)`; `unread_count`, `chat_role` |
| `Message` | UUID PK; soft delete `deleted`; `system_event_type` + `metadata` for system messages |
| `MessageStatus` | `unique_together (message, membership)`; sent → delivered → read |

**Critical index:** `(conversation, created_at)` on `Message` for cursor pagination.

### Notifications (`notifications`)

| Table | Model |
|-------|-------|
| `notification_devices` | `NotificationDevice` — unique `(membership, device_id)` |
| `notification_preferences` | `NotificationPreference` — 1:1 membership |
| `notifications` | `Notification` — history, ordered `-created_at` |

### Platform (`core_platform`)

| Model | Notes |
|-------|-------|
| `PlatformRole` | M2M `rbac.Permission` |
| `PlatformProfile` | OneToOne `User`; `is_active` |

## Migration Strategy

- Per-app migrations under `apps/*/migrations/`
- Recent cross-app changes: department ↔ conversation linking (`companies` 0006), chat system messages (0011), notification app (0001–0003)

Run migrations as part of deploy before traffic shift.

## Transaction Patterns

Services use `@transaction.atomic` for:

- Message send (message + statuses + participant unread + conversation `last_message`)
- Notification create + push dispatch trigger
- Department creation with linked conversation
- Group membership mutations with system messages

## Data Integrity Rules (Enforced in Services)

- User must be `ConversationParticipant` to send messages
- `Membership` must belong to `request.company` for tenant operations
- Invite acceptance creates membership with predetermined role
- Department conversations are `is_system_managed=True`

## Query Hotspots

| Query pattern | Location | Risk |
|---------------|----------|------|
| Conversation list per membership | `chat/selectors.py` | N+1 without prefetch |
| Message cursor pagination | `MessageService` / selectors | Large conversations |
| Permission check per request | `RolePermission` | M2M load — mitigated by prefetch in `CompanyContextPermission` |
| Online presence | Redis, not DB | Good |

## Gaps & Future Schema Work

- No `Project` model despite `Conversation.Type.PROJECT` and RBAC `tenant.project.*`
- No meeting/attendance tables
- `Notification.selectors` module is empty — history listing may be inline in views or missing
- Platform permissions migrated (`0003_delete_platformpermission`) — platform uses shared `rbac.Permission` with `scope=platform`

## Related Documents

- [features/companies.md](./features/companies.md)
- [features/chat.md](./features/chat.md)
- [scalability-considerations.md](./scalability-considerations.md)
