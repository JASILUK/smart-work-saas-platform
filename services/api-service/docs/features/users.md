# Users

## Purpose

Represent global user identity separate from tenant membership. Users may belong to multiple companies via `Membership` records.

## Business Requirements

- One email per user across platform
- Track `active_company` for default tenant context in clients
- Global verification and MFA state
- Profile data minimal on `User` (uses Django `first_name`, `last_name`)

## Models

See [authentication.md](./authentication.md) for `User` and related security models.

**Note:** `GlobalProfile` is commented out in `users/models.py` — not active.

## Architecture

- User CRUD limited; primary mutations through auth/registration services
- `apps/users/selectors.py` for lookups by email/username
- Admin: `apps/users/admin.py`

## Services

User creation delegated to registration services. No dedicated `UserService` — intentional thin model.

## API Endpoints

User profile exposed via `GET /api/users/v1/auth/me/` — not a full user management API.

Employee profile fields live on `Membership` (job_title, work_space_email).

## Permissions & Roles

Global user has no tenant permissions until `Membership` exists.

## Realtime/WebSocket Flows

User ID is not used as chat actor — **membership ID** is the realtime identity within a tenant.

## Validation Rules

- `username` required by AbstractUser but login uses email
- `phone_number` unique when set

## Security Considerations

- `active_company` FK — clients should not trust without verifying membership still active
- User enumeration via registration/login error messages — review messages

## Scalability Concerns

- Single users table — standard B-tree scale
- Social accounts M2M per user — low volume

## Future Improvements

- Activate `GlobalProfile` or merge into user API
- User settings endpoint (timezone, locale)
- Account deletion API (GDPR)
