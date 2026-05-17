# Coding Standards

Conventions observed in this codebase — follow when extending the API service.

## Project Layout

```
apps/{app}/
  models.py
  services/
  selectors.py | selectors/
  api/v1/
    urls.py
    views.py
    serializers.py
  migrations/
```

Shared cross-cutting code belongs in `apps.core`, not duplicated across apps.

## Naming

| Element | Convention | Example |
|---------|------------|---------|
| Services | `{Domain}Service` class, snake_case module | `MessageService`, `message_service.py` |
| Selectors | functions or `{Domain}Selector` | `get_user_conversations` |
| Permissions | `{Context}Permission` | `CompanyContextPermission` |
| API views | `{Resource}{Action}API` or `{Resource}View` | `DepartmentListAPI` |
| Exceptions | `ApplicationError` message string | raised from services |

**Known inconsistency:** `DepartmentSerailzer.py` typo; `emplyee_service.py` typo; `tanent_consumer.py` typo — fix when touching files.

## Views

- Inherit `BaseCompanyAPIView` for tenant endpoints
- Declare `required_permissions = {"GET": "tenant...."}` explicitly
- No ORM writes in views — delegate to services
- Return `success_response` / `error_response` from `apps.core.api_response`

## Services

- Use `@transaction.atomic` for multi-table mutations
- Raise `ApplicationError` for expected business failures
- Side effects after DB state is consistent
- Pass explicit keyword args (`*, membership, conversation`)

## Models

- Inherit `TimeStampedModel` for audit timestamps
- Add `Meta.indexes` for filter columns used in lists
- Use `TextChoices` for enums
- UUID PKs for externally exposed IDs (chat messages/conversations)

## WebSockets

- Use `database_sync_to_async` for ORM in consumers
- Prefer ticket auth over JWT in query strings
- Handler method name must match `type` in `group_send`

## Migrations

- One app per migration chain
- Never edit applied migrations in production branches

## Testing

- `tests.py` files exist but coverage is minimal — add tests with new features
- Use `pytest-django` or Django TestCase per project standard (verify CI)

## Imports

- Absolute imports from `apps.*`
- Avoid circular imports — services should not import views

## Logging

Replace `print()` in consumers with `logging.getLogger(__name__)` for production.

## Related

- [architecture-decisions.md](./architecture-decisions.md)
- [../service-layer-patterns.md](../service-layer-patterns.md)
