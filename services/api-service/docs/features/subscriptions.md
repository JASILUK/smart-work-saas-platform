# Subscriptions (Billing)

## Purpose

Define SaaS plans with feature flags and usage limits; bind one subscription per company; gate tenant API access by subscription status.

## Business Requirements

- Each company has at most one `Subscription`
- Plans seeded for catalog display
- Expired/past-due subscriptions block tenant APIs
- Provider fields reserved for Stripe/payment integration (not fully implemented)

## Models

### `Plan`

| Category | Fields |
|----------|--------|
| Pricing | `price_monthly`, `price_yearly`, `is_free`, `trial_days` |
| Limits | `max_users`, `max_projects`, `max_departments`, `max_storage_gb`, `ai_credits_per_month` |
| Flags | `automation_enabled`, `advanced_analytics`, `custom_branding`, `priority_support`, `api_access`, `custom_roles_enabled` |

### `Subscription`

| Field | Notes |
|-------|-------|
| `status` | trialing, active, past_due, canceled, expired, pending_payment |
| `billing_cycle` | monthly/yearly |
| `trial_ends_at`, `current_period_*` | Billing periods |
| `provider_*` | External billing IDs |

## Architecture

- `subscription_service.py` — create/update subscription on company registration
- `ActiveSubscriptionPermission` on all `BaseCompanyAPIView` endpoints
- Plan enforcement for limits **partially implemented** — flags exist; not all enforced in services

## Services

`subscription_service` — ties company to plan on signup; status transitions (verify call sites).

## Selectors

- `get_subscription_for_company`
- `get_active_plans`

## API Endpoints

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /api/billing/v1/plans/` | Authenticated | List active plans |

**No public subscription management API** (upgrade/cancel) in current urls.

## Permissions & Roles

- Plan list: authenticated user only
- Subscription gate: implicit via `ActiveSubscriptionPermission`
- RBAC code `tenant.subscription.view` in blueprints — verify view usage

## Realtime/WebSocket Flows

None.

## Validation Rules

- Subscription required for company APIs (except where `company` not set on request)
- `EXPIRED` and `PAST_DUE` deny access

## Security Considerations

- Plan changes should be admin-only or payment-webhook driven — no open API today
- Webhook signature validation needed when provider integrated

## Scalability Concerns

- Low traffic catalog — cacheable
- Subscription row 1:1 with company — no hotspot

## Future Improvements

- Stripe webhook endpoints
- Enforce `max_users`, `max_departments` on invite/department create
- Self-service upgrade API
- Usage metering for `ai_credits_per_month`
