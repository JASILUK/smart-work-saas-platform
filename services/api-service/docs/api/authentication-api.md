# Authentication API

Base path: `/api/users/v1/`

## Public Endpoints

| Method | Path | Body / params | Response |
|--------|------|---------------|----------|
| POST | `auth/register/` | email, password, name fields | User created; verification sent |
| POST | `auth/register_with_company/` | user + company fields | User + company + membership |
| POST | `auth/verify-email/` | token | Account verified |
| POST | `auth/resend-verification/` | email | Resend email |
| POST | `auth/email/login/` | email, password | Tokens (+ cookies for web) |
| POST | `auth/mfa/login-verify/` | MFA code | Tokens after MFA challenge |
| POST | `auth/password/forget/` | email | Reset email |
| POST | `auth/password/reset/` | token, new password | Password updated |
| POST | `auth/google/` | Google ID token | User + tokens |
| GET | `auth/csrf/` | — | CSRF token |

## Authenticated Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `auth/logout/` | Blacklist refresh, clear cookies |
| POST | `auth/refresh/token/` | New access token |
| GET | `auth/me/` | Current user |
| POST | `auth/password/change/` | Change password |
| POST | `auth/mfa/setup/` | Begin MFA setup |
| POST | `auth/mfa/verify/` | Confirm MFA device |
| GET | `auth/mfa/devices/` | List devices |
| DELETE | `auth/mfa/device/<id>/` | Remove device |
| POST | `auth/mfa/backup/regenerate/` | New backup codes |

## Auth Mechanisms

**Web:** `Set-Cookie` for `access_token` (HttpOnly) — exact cookie names in `auth_service` / `session_service`.

**Mobile:** `Authorization: Bearer <access_token>`

## Token Lifetimes

From `SIMPLE_JWT` settings:

- Access: 15 minutes
- Refresh: 7 days, rotated, blacklisted after rotation

## Errors

Handled by global `custom_exception_handler` — 401 for invalid/expired tokens.

## Headers

No `X-Company-ID` required on auth endpoints.

## Related

- [../features/authentication.md](../features/authentication.md)
- [../api-standards.md](../api-standards.md)
