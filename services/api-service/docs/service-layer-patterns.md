# Service Layer Patterns

## Principle

**Views and serializers do not contain business rules.** Services own:

- Validation beyond DRF field-level checks
- Database transactions
- Side effects (email, Celery, channel broadcasts, push)
- Cross-model orchestration

## Naming & Location

| Pattern | Example |
|---------|---------|
| `{domain}_service.py` | `message_service.py`, `notification_service.py` |
| PascalCase class | `MessageService`, `DepartmentService` |
| `apps/{app}/services/` | Primary location |

**Inconsistency:** `MessageService.py` vs `message_service.py` both exist in chat — pagination helper in one, main service in the other.

## Common Decorators & Utilities

```python
@staticmethod
@transaction.atomic
def send_message(...):
    ...
```

- `get_object_or_404` for single-entity fetches in services (acceptable)
- `ApplicationError("message")` for business failures → 400 in exception handler
- `async_to_sync(channel_layer.group_send)` for realtime from sync code

## Orchestration Examples

### Message send (`MessageService.send_message`)

1. Load conversation; verify participant
2. Validate content/file
3. Create `Message`
4. `_handle_delivery` — status rows, unread counts
5. Update conversation `last_message`
6. `_broadcast_message` — channel groups
7. `_notify_offline_users` — notification service

### Department create (`department_application_service`)

1. Create `Department`
2. Create system-managed `Conversation` type DEPARTMENT
3. Link `department.conversation`
4. Add participants from department members
5. Optional system message via `system_message_service`

### Invite accept (`invite_service`)

1. Validate token hash and expiry
2. Create `Membership` with role/department from invite
3. Mark invite used
4. Signal may create `NotificationPreference`

## Side Effect Boundaries

| Side effect | Where |
|-------------|-------|
| Email | Celery tasks (`invite_tasks`, `notification_tasks`) |
| Push | `PushService` → Celery `push_tasks` |
| WebSocket | `MessageService`, `group_realtime_service`, consumer |
| File upload | `media_storage_service.upload_file` (Cloudinary) |

Prefer enqueueing Celery **after** transaction commit for external IO (verify per call site).

## Anti-Patterns Observed

| Issue | Location | Recommendation |
|-------|----------|----------------|
| `print()` debugging | `TenantConsumer` | Structured logging |
| Direct Redis in service + consumer | chat | Centralize presence module |
| Empty selector module | notifications | Move queries out of views |
| Business logic in views | Some older views | Migrate to services |

## Testing Services

- Unit test services with Django DB fixtures
- Mock `channel_layer` and Celery `.delay` for isolation
- WebSocket flows need `channels.testing.WebsocketCommunicator` integration tests

## Related Documents

- [selector-patterns.md](./selector-patterns.md)
- [api-standards.md](./api-standards.md)
- [engineering/coding-standards.md](./engineering/coding-standards.md)
