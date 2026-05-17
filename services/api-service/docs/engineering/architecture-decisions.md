# Architecture Decisions

Recorded decisions inferred from the current implementation. ADR numbers are local to this doc.

## ADR-001: Header-Based Tenancy

**Decision:** Use `X-Company-ID` header rather than subdomain or path tenancy.

**Rationale:** Simplifies gateway routing; one API host serves all companies.

**Tradeoffs:** Clients must send header; risk of wrong company if client bug — mitigated by membership validation.

## ADR-002: Membership as Chat Actor

**Decision:** Messages reference `Membership`, not `User`.

**Rationale:** Same user in two companies has isolated chat identity and permissions.

## ADR-003: Service + Selector Split

**Decision:** Writes in services; reads in selectors.

**Rationale:** Testability and DRF view thinness.

**Gap:** Not all apps enforce strictly (empty notification selectors).

## ADR-004: Cookie-First JWT for Web

**Decision:** `UniversalJWTAuthentication` reads HttpOnly cookie before Authorization header.

**Rationale:** XSS-resistant token storage for browser clients; mobile keeps Bearer.

## ADR-005: WebSocket Ticket Auth

**Decision:** Short-lived cache ticket for WS; JWT fallback.

**Rationale:** Avoid long-lived tokens in URLs and logs.

## ADR-006: Redis Dual Use

**Decision:** Redis for Channels, Celery, Django cache, and raw presence keys.

**Rationale:** Operational simplicity for small/medium deploys.

**Tradeoffs:** Blast radius; DB index separation (`/0`, `/1`, `/2`) partially mitigates.

## ADR-007: Per-Recipient MessageStatus

**Decision:** `MessageStatus` row per (message, membership).

**Rationale:** Accurate WhatsApp-style receipts in groups.

**Tradeoffs:** Storage growth; connect-time bulk updates.

## ADR-008: System-Managed Department Conversations

**Decision:** `Department.conversation` OneToOne, `is_system_managed=True`.

**Rationale:** Department chat lifecycle tied to org structure.

## ADR-009: RBAC Permission Codes

**Decision:** String codes in DB with wildcard seed patterns (`tenant.*`).

**Rationale:** Flexible admin UI and role editing.

**Gap:** Platform blueprints empty; `api/platform/v1` miswired.

## ADR-010: Firebase for Push

**Decision:** FCM via `firebase-admin` with Celery async send.

**Rationale:** Standard mobile push; decouple from WS delivery.

## Deferred / Not Decided

| Topic | State |
|-------|-------|
| Payment provider | Fields on Subscription only |
| Meetings / attendance | Notification prefs only |
| AI / automation | Plan flags only |
| Event sourcing | Not used |
| Read replicas | Not configured |

## Related

- [../backend-architecture.md](../backend-architecture.md)
- [future-roadmap.md](./future-roadmap.md)
