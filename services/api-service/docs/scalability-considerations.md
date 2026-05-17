# Scalability Considerations

## Current Topology

Single Django ASGI deployment with:

- PostgreSQL (single primary assumed)
- Redis — shared for Channels, Celery, cache, raw presence
- Cloudinary for media
- No read replicas or sharding in code

## Horizontal Scaling

| Component | Scale approach |
|-----------|----------------|
| HTTP/WS workers | Multiple Uvicorn/Daphne workers behind load balancer |
| Channel layer | Redis — must be shared across workers |
| Celery workers | Scale independently |
| PostgreSQL | Vertical scale first; read replicas need selector routing |

**Sticky sessions not required** for HTTP (JWT). WebSockets require LB WebSocket support or dedicated WS tier.

## Database Bottlenecks

| Hot path | Concern |
|----------|---------|
| `Message` by `(conversation_id, created_at)` | High write volume in active tenants |
| `MessageStatus` rows | N participants × M messages — growth O(participants × messages) |
| `ConversationParticipant.unread_count` | Updated on every message |
| Permission prefetch | Per request — acceptable with prefetch |
| Connect delivery sync | Updates all SENT statuses for user on every WS connect |

### Recommendations

- Partition or archive old messages by company/date
- Consider denormalized read cursor instead of per-message status for large groups
- Index review on `MessageStatus(membership_id, status)`

## Redis

| Use | DB/index | Contention |
|-----|----------|------------|
| Celery broker | /0 | High under task load |
| Celery results | /1 | Medium |
| Django cache / WS tickets | /2 | Medium |
| Channel layer | separate config host | High with many WS |
| Presence keys | same REDIS_URL | Per-tenant sets grow with users |

**Risk:** Single Redis instance is a blast radius. Split Celery, Channels, and cache for large deployments.

## WebSocket Fan-out

Each message send triggers:

- Room group broadcast
- Per-recipient user group messages
- Status update broadcasts

Large groups (100+ participants) will stress channel layer — consider limiting group size or using fan-out workers.

## Celery

Push notifications async — good. Ensure task idempotency for retries.

Missing beat schedule — periodic cleanup relies on manual/missing cron (`cleanup_tasks` exists).

## Caching Opportunities

| Data | TTL candidate |
|------|---------------|
| Permission codes per role | Minutes |
| Plan list | Hours |
| Company context | Request-scoped only today |
| Conversation list | Short TTL with invalidation on WS events |

## Async Readiness

- Consumers are async; ORM via `database_sync_to_async`
- HTTP stack remains sync Django views
- Heavy CPU work (image processing) delegated to Cloudinary

## Multi-Region

Not supported — all data in one PostgreSQL. Future: tenant pinning or global DB with latency tradeoffs.

## Related Documents

- [deployment-readiness.md](./deployment-readiness.md)
- [websocket-architecture.md](./websocket-architecture.md)
- [engineering/future-roadmap.md](./engineering/future-roadmap.md)
