# Security Considerations

## Authentication

| Control | Implementation | Notes |
|---------|----------------|-------|
| Password hashing | Django `AbstractUser` | Standard validators in settings |
| JWT access | 15 min lifetime | Short-lived |
| JWT refresh | 7 days, rotate + blacklist | Good practice |
| MFA | TOTP/SMS devices + backup codes | Separate login verify flow |
| OAuth | Google ID token verification | GitHub integration exists; verify exposure |
| Email verification | `VerificationToken` | Required for full account trust |

### Cookie security

`base.py` sets `CSRF_COOKIE_SECURE = False`, `SESSION_COOKIE_SECURE = False` — **must be True behind HTTPS in production**.

## Authorization

| Layer | Risk |
|-------|------|
| Tenant isolation | Depends on `X-Company-ID` + membership check — clients can spoof header but server validates membership |
| RBAC | Method-level codes; gaps when `required_permissions` omitted |
| Chat participant check | Enforced on send; **not on WS room join** |
| Platform APIs | Unmounted — reduces attack surface but also blocks legitimate admin ops |

## WebSocket

| Risk | Severity | Mitigation |
|------|----------|------------|
| JWT in query string | Medium | Prefer one-time tickets; avoid logging URLs |
| Room join without participant check | High | Validate `ConversationParticipant` in `join_room` |
| Ticket replay | Low | Cache delete on use |
| Cross-tenant | Medium | Ensure `tenant_id` always from ticket, not client body |

## Secrets Management

| Finding | Action |
|---------|--------|
| `firebase/service-account.json` in repository | Remove from git; use env/vault only |
| `SECRET_KEY` from env | Required |
| `GOOGLE_CLIENT_SECRET` in env | OK |

## Data Protection

- Passwords never returned in serializers
- MFA secrets stored in DB — ensure encryption at rest for production DB
- Invite tokens: `token_hash` stored, UUID `token_id` in link
- Message soft-delete — content may remain until hard-delete policy defined

## Input Validation

- DRF serializers on API boundaries
- `ApplicationError` for business rules in services
- File uploads: MIME sniffing via `resolve_message_type` — add size limits and malware scanning for production

## CORS

Explicit allowlist in `CORS_ALLOWED_ORIGINS`. Credentials enabled — do not use `*` with credentials.

## Rate Limiting

**Not implemented** in codebase — recommend gateway-level or DRF throttling for auth, invite, message send.

## Push Notifications

FCM tokens stored per device — treat as sensitive; deactivate on logout.

## Compliance Readiness

| Area | Status |
|------|--------|
| Audit log for admin actions | Not present |
| Data export/delete per user | Not implemented |
| Message retention policy | Not codified |

## Related Documents

- [permissions-system.md](./permissions-system.md)
- [deployment-readiness.md](./deployment-readiness.md)
- [engineering/known-issues.md](./engineering/known-issues.md)
