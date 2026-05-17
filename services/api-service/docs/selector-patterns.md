# Selector Patterns

## Purpose

Selectors encapsulate **read paths** — query construction, filtering, prefetching, and pagination cursors — without mutating state.

Convention: functions or selector classes in `selectors.py` or `selectors/` packages.

## Implemented Selectors

### `apps/users/selectors.py`

- `get_user_by_email`, `get_user_by_username`
- MFA device lookups
- Verification token: `get_latest_unused_token`

### `apps/chat/selectors.py`

- `get_direct_conversation(company, membership_a, membership_b)`
- `get_user_conversations(membership)` — conversation list for sidebar
- `get_conversation_messages(conversation_id, cursor, limit)` — message history

### `apps/companies/selectors/DepartmentSelectors.py`

- `DepartmentSelector` — department trees, by company, with head/conversation prefetch

### `apps/companies/selectors/Employee_selectors.py`

- `EmployeeSelector` — membership lists, filters
- `get_pending_company_by_owner`

### `apps/billing/selectors.py`

- `get_subscription_for_company`
- `get_active_plans`

### `apps/rbac/selectors.py`

- Role/permission query helpers (if present — used by services)

### `apps/core_platform/selectors.py`

- `PlatformRoleSelector`

### `apps/notifications/selectors/notification_selectors.py`

- **Empty file** — queries likely inline in views/services today

## Optimization Patterns

### Prefetch in permission layer

`CompanyContextPermission` already does:

```python
.select_related("company", "role")
.prefetch_related("role__permissions")
```

### Chat list queries

Conversation list should prefetch:

- `last_message`
- `participants__membership__user`
- Annotate unread from `ConversationParticipant`

Verify `get_user_conversations` implementation when optimizing.

### Cursor pagination

`MessageCursorPagination` in `MessageService.py` — time-based or ID-based cursors for infinite scroll.

## When to Add a Selector

Add or extend a selector when:

- The same queryset is used from a view and a service
- You need consistent `select_related` / `prefetch_related`
- Complex filters (department tree, employee search)

Keep writes in services only.

## Gaps

| Gap | Risk |
|-----|------|
| Empty notification selectors | Duplicated ORM in views |
| No shared "membership in company" selector | Repeated filter logic |
| Project/conversation queries scattered | Hard to optimize globally |

## Related Documents

- [service-layer-patterns.md](./service-layer-patterns.md)
- [scalability-considerations.md](./scalability-considerations.md)
