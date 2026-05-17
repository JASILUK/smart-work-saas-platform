# Departments

## Purpose

Organizational structure within a company with hierarchical departments, department head, member assignment, and **system-managed department chat**.

## Business Requirements

- Departments belong to one company
- Optional parent for org tree
- One primary conversation per department (type `DEPARTMENT`)
- Head is a `Membership` reference
- Members assigned via membership.department or assign API

## Models

`Department` — see [companies.md](./companies.md).

Relationship:

```
Department ──OneToOne──► Conversation (is_system_managed=True, type=department)
Department.head ──FK──► Membership
Membership.department ──FK──► Department
```

## Architecture

Department mutations split:

- `DepartmentService` — core CRUD
- `department_application_service` — transactional create with chat
- `department_membership_service` — member assign/remove/transfer
- `department_chat_service` — participant sync, system messages

## Services

### Create workflow (`department_application_service`)

1. Validate company scope and permissions (via view)
2. Create `Department`
3. Create `Conversation` with `type=DEPARTMENT`, `is_system_managed=True`
4. Set `department.conversation`
5. Add existing department members as `ConversationParticipant`
6. Emit system message if configured

### Membership changes

Assign/update `Membership.department` and sync chat participants.

## Selectors

`DepartmentSelector` — list/detail with company filter, optional tree.

## API Endpoints

Under `/api/company/v1/departments/` — see companies feature doc.

| Method | Permission |
|--------|------------|
| GET list | `tenant.department.view` |
| POST create | `tenant.department.create` |
| GET/PATCH/DELETE detail | view/update codes |
| assign/remove/transfer | dedicated codes per view |

## Permissions & Roles

Standard tenant RBAC. Chat access derived from conversation participation, not separate department permission.

## Realtime/WebSocket Flows

- New department conversation → `conversation_created` event
- Member add → system message + participant broadcast
- Uses `group_realtime_service` patterns

## Validation Rules

- Name unique per company
- Head must be member of company
- Cannot delete department with members without policy (verify view)
- Parent department must be same company

## Security Considerations

- Department chat includes all participants — removing membership must remove participant row
- System-managed conversations should block manual delete in API (verify)

## Scalability Concerns

- Deep department trees — recursive queries
- Large departments → large conversation participant sets

## Future Improvements

- Sub-department permission inheritance
- Multiple channels per department (announcements vs chat)
- Department archive workflow
