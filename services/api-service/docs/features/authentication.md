# Authentication

## Purpose

Provide secure identity lifecycle: registration, email verification, password reset, JWT session management (web cookies + mobile Bearer), MFA, and Google OAuth login.

## Business Requirements

- Email-as-username identity (`User.email` unique)
- Optional phone verification fields (not fully wired in all flows)
- Support web (HttpOnly cookies) and mobile (Authorization header)
- MFA for elevated account security
- Company registration path combines user + company creation

## Models

| Model | Responsibility |
|-------|----------------|
| `User` | Core identity; `is_verified`, `active_company` |
| `VerificationToken` | EMAIL_VERIFY, PASSWORD_RESET, INVITE, TWO_FACTOR |
| `MFADevice` | TOTP/SMS secrets |
| `BackupCode` | MFA recovery |
| `SocialAccount` | OAuth provider linkage |

## Architecture

| Layer | Module |
|-------|--------|
| Services | `auth_service`, `registration`, `register_with_company`, `password_service`, `session_service`, `MFA_service`, `OauthService`, `verification` |
| Strategies | `auth_strategies`, `verification_strategies` |
| Auth backend | `UniversalJWTAuthentication` |

Login flows select strategy by credential type; tokens issued via SimpleJWT with rotation/blacklist.

## Services

| Service | Workflow |
|---------|----------|
| `registration` | Create user, send verification email |
| `register_with_company` | User + company + owner membership + subscription bootstrap |
| `auth_service` | Login, token pair, cookie attachment |
| `session_service` | Refresh, logout, blacklist |
| `MFA_service` | Setup, verify, backup codes |
| `OauthService` | Google token → user create/link |

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST auth/register/` | User-only registration |
| `POST auth/register_with_company/` | User + company |
| `POST auth/verify-email/` | Confirm email token |
| `POST auth/resend-verification/` | Resend verification |
| `POST auth/email/login/` | Standard login |
| `POST auth/mfa/login-verify/` | Complete MFA challenge |
| `POST auth/refresh/token/` | Refresh access token |
| `POST auth/logout/` | Invalidate session |
| `GET auth/me/` | Current user profile |
| `POST auth/password/forget|reset|change/` | Password flows |
| `POST auth/mfa/setup|verify/` | MFA lifecycle |
| `GET/DELETE auth/mfa/devices/` | Device management |
| `POST auth/google/` | Google OAuth |
| `GET auth/csrf/` | CSRF token for cookie clients |

Permissions: public for register/login/verify; authenticated for me/MFA/password change.

## Permissions & Roles

Authentication endpoints are **outside** tenant RBAC. Company context not required.

## Realtime/WebSocket Flows

None.

## Validation Rules

- Email uniqueness on registration
- Token `is_valid()` checks expiry and `is_used`
- Password validators (Django defaults)
- MFA verify before marking device active

## Security Considerations

- Prefer HttpOnly + Secure + SameSite cookies in production
- JWT in WebSocket query string is weaker than ticket auth for chat
- Backup codes single-use — ensure constant-time comparison
- Google token verified server-side via Google API

## Scalability Concerns

- Email/SMS via Celery `send_notification_task` — scale workers for burst signups
- Token table growth — periodic cleanup job

## Future Improvements

- Rate limit login and password reset
- Phone OTP completion
- Apple/GitHub OAuth parity with Google
- Session device management UI
