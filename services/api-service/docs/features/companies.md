# Companies

## Purpose

Multi-tenant company (organization) management: membership, departments, employee admin, and invitation workflows.

## Business Requirements

- Company lifecycle: pending → active (via activation service)
- Owner-protected company record
- Employees are memberships with roles and optional departments
- Invites: single, bulk, CSV
- Departments with optional head and linked department chat

## Models

| Model | Key fields / constraints |
|-------|--------------------------|
| `Company` | `slug` unique, `status`, `owner` |
| `Membership` | `unique_together (user, company)`, `role`, `department`, `is_active`, `last_seen` |
| `Department` | `unique_together (company, name)`, `parent` tree, `head`, `conversation` OneToOne |
| `CompanyInvite` | hashed token, `expires_at`, role + department preset |

## Architecture

```
BaseCompanyAPIView
  → CompanyContextPermission
  → ActiveSubscriptionPermission
  → RolePermission
```

Services orchestrate cross-app effects (chat conversation on department create).

## Services

| Service | Responsibility |
|---------|----------------|
| `company_service` | Company CRUD basics |
| `company_activation_service` | Pending → active |
| `company_context_service` | Current company context for user |
| `membership_service` | Membership mutations |
| `DepartmentService` | Department queries/mutations |
| `department_application_service` | Create department + conversation workflow |
| `department_membership_service` | Assign/remove/transfer members |
| `invite_service` | Create/accept invites |
| `bulk_invite_service` | Batch invites |
| `csv_parser` | CSV upload parsing |
| `emplyee_service` | Block/unblock, employee operations |

## Selectors

- `DepartmentSelector`
- `EmployeeSelector`, `get_pending_company_by_owner`

## Serializers

Located in `apps/companies/api/v1/serializers/` — `DepartmentSerailzer` (typo in filename), invite serializers, employee serializers.

## API Endpoints

| Endpoint | Permission (typical) |
|----------|----------------------|
| `POST invite/users/` | Invite create |
| `POST invite/bulk/users/` | Bulk invite |
| `POST invite/bulk_in_csv/users/` | CSV invite |
| `GET invite/detailes/` | Invite metadata |
| `POST invite/accept/` | Public/authenticated accept |
| `GET context/` | Current company context |
| `GET/POST employee/` | List employees |
| `GET employee/<pk>/` | Detail |
| `POST employee/<pk>/block|unblock/` | `tenant.employee.block` |
| `GET/POST departments/` | List/create |
| `GET/PATCH/DELETE departments/<pk>/` | Detail |
| `POST departments/<pk>/assign-member/` | Assign to department |
| `POST departments/<pk>/remove-member/` | Remove |
| `POST departments/<pk>/transfer-member/` | Transfer |

## Permissions & Roles

Requires `X-Company-ID`. Method-level codes on department and employee views.

## Realtime/WebSocket Flows

- `last_seen` updated on WS disconnect
- Department membership changes sync chat participants via `department_chat_service`

## Validation Rules

- Cannot assign membership outside company
- Department name unique per company
- Invite expiry enforced on accept
- Head must be membership in same company

## Security Considerations

- Invite tokens hashed at rest
- Block sets `is_active=False` — verify chat access revoked
- CSV upload — validate file size and row limits

## Scalability Concerns

- Bulk invite → Celery email tasks — queue depth under large CSV
- Department tree queries — use `select_related` on parent chains

## Future Improvements

- Company settings API
- Audit log for employee block/role change
- Enforce `max_departments` from `Plan`
