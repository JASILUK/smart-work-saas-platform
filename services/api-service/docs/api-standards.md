# API Standards

## Base URL & Versioning

All REST APIs are versioned under `/api/{domain}/v1/`.

| Domain | Prefix |
|--------|--------|
| Users / auth | `/api/users/v1/` |
| Company / HR | `/api/company/v1/` |
| RBAC | `/api/rbac/v1/` |
| Billing | `/api/billing/v1/` |
| Chat | `/api/chat/v1/` |
| Notifications | `/api/notification/v1/` |

Note: `/api/platform/v1/` duplicates RBAC routes — not platform admin API.

## Authentication

| Client | Method |
|--------|--------|
| Web | HttpOnly cookie `access_token` |
| Mobile / API | `Authorization: Bearer <access_token>` |

`UniversalJWTAuthentication` tries cookie first, then header.

Refresh: `POST /api/users/v1/auth/refresh/token/`  
Logout: blacklists refresh token via SimpleJWT blacklist app.

## Tenant Context Header

```
X-Company-ID: <company_pk>
```

Required for all `BaseCompanyAPIView` subclasses. Missing header → 403 from `CompanyContextPermission`.

Optional related header (CORS allowed):

```
x-client-type: web | mobile
```

## Response Envelope

`apps.core.api_response`:

- `success_response(data, message, status)`
- `error_response(message, errors, status)`

Global exception handler maps `ApplicationError` and DRF exceptions to consistent JSON.

## HTTP Methods & Permissions

Tenant views declare:

```python
class DepartmentListAPI(BaseCompanyAPIView):
    required_permissions = {
        "GET": "tenant.department.view",
        "POST": "tenant.department.create",
    }
```

If method not listed, `RolePermission` allows any company member with valid subscription.

## Pagination

- Chat messages: cursor-based (`MessageCursorPagination`)
- List endpoints: verify per view — many use full lists without DRF pagination classes

## File Uploads

Multipart form data to message send and company logo endpoints. Files routed through Cloudinary upload service.

## WebSocket Ticket API

```
POST /api/chat/v1/ws-ticket/
```

Requires authenticated user + company context. Returns short-lived ticket for `ws/app/` connection.

## Error Codes

| Situation | Typical status |
|-----------|----------------|
| Unauthenticated | 401 |
| Missing company header / not a member | 403 |
| Expired subscription | 403 |
| Missing permission code | 403 |
| Business rule violation (`ApplicationError`) | 400 |
| Not found | 404 |

## Idempotency

Not formally implemented (no `Idempotency-Key` header). Invite accept and message send rely on DB constraints.

## Related API Docs

- [api/authentication-api.md](./api/authentication-api.md)
- [api/chat-api.md](./api/chat-api.md)
- [api/notifications-api.md](./api/notifications-api.md)
