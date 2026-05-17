# Permissions System

## Model

Permissions are **code-based strings** stored in `rbac.Permission`:

| Field | Purpose |
|-------|---------|
| `code` | Unique identifier, e.g. `tenant.employee.view` |
| `scope` | `tenant` or `platform` |
| `category` | UI grouping |
| `name`, `description` | Human-readable |

Roles are **per-company** (`rbac.Role`):

- `company` FK
- `permissions` M2M
- `is_system_role` — seeded roles (Owner, Admin, Member)

Platform staff use `core_platform.PlatformRole` (also M2M to `rbac.Permission`).

## Seeding

`python manage.py seed_permission` reads `apps/rbac/conf.py`:

- `TENANT_ROLE_BLUEPRINTS` — Owner (`tenant.*`), Admin, Member pattern lists
- `PLATFORM_ROLE_BLUEPRINTS` — **empty** in production config
- `later_will_add_platform` — documented future patterns, **not active**

## HTTP Permission Stack (Tenant APIs)

`BaseCompanyAPIView` applies in order:

1. `IsAuthenticated`
2. `CompanyContextPermission` — requires header `X-Company-ID`, sets `request.company`, `request.membership`
3. `ActiveSubscriptionPermission` — blocks `expired` / `past_due` subscription
4. `RolePermission` — checks `view.required_permissions[HTTP_METHOD]`

### CompanyContextPermission

```python
# apps/companies/permissions.py
company_id = request.headers.get("X-Company-ID")
Membership.objects.select_related("company", "role")
    .prefetch_related("role__permissions")
    .filter(user=request.user, company_id=company_id, is_active=True)
```

Fails closed if header missing or membership inactive.

### RolePermission

```python
permission_code = view.required_permissions.get(request.method)
if not permission_code:
    return True  # endpoint open to any authenticated member with company context
return permission_code in {p.code for p in membership.role.permissions.all()}
```

**Convention:** Declare `required_permissions` dict on each view class.

### ActiveSubscriptionPermission

Allows request if no `request.company`. Otherwise requires `company.subscription` not in `EXPIRED`, `PAST_DUE`.

Sets `request.subscription` when valid.

## Platform APIs

`BasePlatformAPIView` uses `PlatformPermission`:

- Requires `request.user.platform_profile` active
- Checks `view.required_permissions` against `platform_profile.role.permissions`

**Routing gap:** `apps.core_platform.api.v1.urls` is not mounted; `api/platform/v1/` currently serves **tenant RBAC** URLs instead.

## Example Permission Codes (In Use)

| Code | Views |
|------|-------|
| `tenant.employee.view` | Employee list/detail |
| `tenant.employee.block` | Block/unblock |
| `tenant.department.view` | Department list |
| `tenant.department.create` | Department create |
| `tenant.department.update` | Department detail mutations |
| `tenant.role.create` | Role APIs |
| `platform.role.view` | Platform role views (unmounted) |

Blueprint also references `tenant.project.*` — **no project feature implemented**.

## Chat Authorization

Chat does **not** use `RolePermission` on all endpoints — relies on:

- `BaseCompanyAPIView` or equivalent auth
- **Participant membership** checks inside `MessageService` / group services

RBAC does not gate individual message send at permission-code level today.

## WebSocket Authorization

- Connection: valid user + tenant membership via middleware
- Room join: **no RBAC check** — only connection-level tenant binding
- Risk: any connected member could subscribe to room groups if they guess UUIDs

## Billing vs Permissions

Subscription status is orthogonal to RBAC — both must pass for tenant APIs using `BaseCompanyAPIView`.

Plan flags (`custom_roles_enabled`, etc.) are on `Plan` model but **not consistently enforced** in role creation views (verify before relying on).

## Related Documents

- [features/companies.md](./features/companies.md)
- [security-considerations.md](./security-considerations.md)
- [api-standards.md](./api-standards.md)
