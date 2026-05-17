# Deployment Readiness

## Container

`Dockerfile`:

- Base: `python:3.10-slim`
- Installs `libjpeg-dev`, `zlib1g-dev`, `gcc` for image libs
- `pip install -r requirements.txt`
- Copies app to `/app`

**Gaps:** No `CMD`/`ENTRYPOINT` in Dockerfile snippet — orchestration must define run command (e.g. `daphne`, `gunicorn`, `celery`).

## Settings Environments

| Module | Purpose |
|--------|---------|
| `config.settings.base` | Shared defaults |
| `config.settings.local` | Development |
| `config.settings.production` | Production overrides |

ASGI uses `DJANGO_ENV` to select settings module (default `local`).

### Production checklist

| Item | base.py state | Required action |
|------|---------------|-----------------|
| `DEBUG` | `True` | Set `False` in production |
| `SECRET_KEY` | env | Must be strong, rotated |
| `ALLOWED_HOSTS` | localhost, gateway, api | Add production domains |
| Cookie secure flags | False | Enable HTTPS cookies |
| `CORS_ALLOWED_ORIGINS` | localhost only | Add frontend origins |
| Static files | WhiteNoise | Run `collectstatic` |
| Firebase credentials | file path env | Mount secret, not image layer |

## Process Model

| Process | Entry |
|---------|-------|
| HTTP + WS | ASGI: `config.asgi:application` |
| Celery worker | `celery -A config worker` |
| Celery beat | `celery -A config beat` (if schedules added) |
| Migrations | `python manage.py migrate` |

## Dependencies (Infrastructure)

| Service | Config |
|---------|--------|
| PostgreSQL | `POSTGRES_*`, `DB_HOST` |
| Redis | `REDIS_URL` — used for cache DB 2, Celery 0/1, Channels, presence |
| Cloudinary | `CLOUDINARY_*` |
| Email | `EMAIL_PROVIDER`, SMTP vars |
| SMS | `SMS_PROVIDER` |
| Firebase | `FIREBASE_CREDENTIALS` path |

## Health Checks

No dedicated `/health/` endpoint in `config/urls.py` — **add for k8s/load balancer**.

Suggested checks:

- DB connectivity
- Redis ping
- Channel layer optional

## Migrations & Seeds

Deploy order:

1. Run migrations
2. `seed_permission` (new environments)
3. `seed_plans` (billing catalog)
4. `backfill_notification_preferences` (if upgrading existing memberships)

## Observability Gaps

| Gap | Recommendation |
|-----|----------------|
| `print()` in consumers | JSON structured logging |
| No request ID middleware | Add correlation IDs |
| No APM hooks | Sentry/Datadog integration |
| Celery task failures | Monitor broker dead letter |

## Secrets in Git

`.gitignore` should exclude:

- `.env`
- `firebase/service-account.json`

Verify credentials are not in container images pushed to public registries.

## Gateway Integration

`ALLOWED_HOSTS` includes `gateway`, `api`, `api_service` — service expects reverse proxy from platform gateway.

Headers to forward:

- `Authorization` / cookies
- `X-Company-ID`
- WebSocket upgrade headers

## Related Documents

- [security-considerations.md](./security-considerations.md)
- [engineering/current-system-state.md](./engineering/current-system-state.md)
