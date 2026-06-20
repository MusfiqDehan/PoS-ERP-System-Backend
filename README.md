# Sortorium Backend

Django 6 multi-tenant Point of Sale API built with **django-tenants**, **Django REST Framework**, **Celery**, **Redis**, and **PostgreSQL 18**. The ASGI server is **Daphne** (port **8002**).

## Stack

| Component | Local | Production |
|-----------|-------|------------|
| App server | Daphne on `:8002` | Daphne via `scripts/run-asgi-prod.sh` |
| Database | PostgreSQL 18.4 | PostgreSQL 18.4 + PgBouncer |
| Cache / broker | Redis 8.8 | Redis 8.8 |
| Task queue | Celery worker + beat | Celery worker + beat |
| Reverse proxy | — | Traefik (external network) |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2
- For production: a running **Traefik** instance on the external `traefik_proxy` network

## Quick start (local)

```bash
cd Sortorium_Backend

# 1. Create environment files
cp .env.example .env.local
cp .env.local.celery.example .env.local.celery

# 2. Edit .env.local — at minimum set POSTGRES_* and SUPERADMIN_* values.
#    For Docker Compose, DATABASE_URL should point at the db service:
#    DATABASE_URL=postgresql://<user>:<password>@db:5432/<dbname>

# 3. Build and start all services
docker compose -f docker-compose.local.yml up --build -d

# 4. Check logs (first boot runs migrations + seeds superadmin)
docker compose -f docker-compose.local.yml logs -f backend
```

**API:** http://localhost:8002  
**OpenAPI docs:** http://localhost:8002/api/v1/docs/ (local settings only)

### Local services

| Service | Container | Host port | Internal port |
|---------|-----------|-----------|---------------|
| Backend | `sortorium-backend-local` | 8002 | 8002 |
| PostgreSQL | `sortorium-db-local` | 5452 | 5432 |
| Redis | `sortorium-redis-local` | 6380 | 6379 |
| Celery worker | `sortorium-celery-worker-local` | — | — |
| Celery beat | `sortorium-celery-beat-local` | — | — |

On first start the backend **entrypoint** automatically:

1. Collects static files
2. Runs shared + tenant schema migrations
3. Syncs the feature registry
4. Seeds platform roles
5. Creates the superadmin account (from `SUPERADMIN_EMAIL` / `SUPERADMIN_PASSWORD`)

Celery services set `SKIP_DB_BOOTSTRAP=1` so they start without re-running migrations.

### Local dev tooling

When `DEBUG=true` and `DJANGO_SETTINGS_MODULE=config.settings.local`:

| Tool | URL |
|------|-----|
| OpenAPI (Swagger) | `/api/v1/docs/` |
| Debug toolbar | `/__debug__/` |
| Silk profiler | `/silk/` |

First-time Silk setup on the host (outside Docker):

```bash
DJANGO_SETTINGS_MODULE=config.settings.local python manage.py migrate_schemas --shared
```

## Environment configuration

Copy the template and maintain separate files per environment:

```bash
cp .env.example .env.local
cp .env.local.celery.example .env.local.celery
cp .env.example .env.prod
cp .env.pgbouncer.prod.example .env.pgbouncer.prod
```

### Env file layout

Docker Compose loads configuration **only** from env files — no inline `environment:` blocks in compose.

| File | Used by |
|------|---------|
| `.env.local` | `backend`, `db`, shared vars for Celery |
| `.env.local.celery` | `celery_worker`, `celery_beat` (local only; sets `SKIP_DB_BOOTSTRAP=1`) |
| `.env.prod` | `backend`, `celery_worker`, `celery_beat`, `db` |
| `.env.pgbouncer.prod` | `pgbouncer` only (`DATABASE_URL` → `db:5432`, pool settings) |

Example templates (committed): `.env.example`, `.env.local.celery.example`, `.env.pgbouncer.prod.example`

### Key variables

| Variable | Local (Docker) | Production |
|----------|----------------|------------|
| `DJANGO_SETTINGS_MODULE` | `config.settings.local` (in `.env.local`) | `config.settings` (in `.env.prod`) |
| `SKIP_DB_BOOTSTRAP` | `1` in `.env.local.celery` only | `1` in `.env.prod` |
| `DATABASE_URL` | `postgresql://…@db:5432/…` | `postgresql://…@pgbouncer:6432/…` |
| `DIRECT_DATABASE_URL` | — | `postgresql://…@db:5432/…` (migrations only) |
| `REDIS_PASSWORD` | `sortorium_redis_local` in `.env.local` | Strong secret in `.env.prod` (must match URLs below) |
| `REDIS_*` / `CELERY_*` | `redis://:PASSWORD@redis:6379/…` in `.env.local` | `redis://:PASSWORD@redis:6379/…` in `.env.prod` |
| `PUBLIC_DOMAIN` | `localhost` | `sortorium.com` |
| `PORT` | `8002` | `8002` |
| `ASGI_WORKERS` | — | `2` in `.env.prod` |

**Host machine access** (connecting to Docker-published ports without joining the compose network):

- PostgreSQL: `localhost:5452`
- Redis: `localhost:6380` (auth required — see `REDIS_PASSWORD` in `.env.local`)
- Backend: `localhost:8002`

See `.env.example` for the full list including CORS, CSRF, tenancy, email, and rate-limit settings.

### PostgreSQL credentials (Docker)

The `db` service reads standard Postgres image variables from your env file:

```env
POSTGRES_DB=sortorium_db
POSTGRES_USER=sortorium_user
POSTGRES_PASSWORD=change-me
```

PostgreSQL 18 stores data under `/var/lib/postgresql` (versioned subdirectory, e.g. `18/docker/`). Do **not** mount `/var/lib/postgresql/data` with PG 18.

## Production deployment

Production uses `docker-compose.prod.yml` with Traefik for TLS termination, PgBouncer for connection pooling, and resource limits per service.

### Prerequisites

1. **DNS** — `sortorium.com` and `*.sortorium.com` point to the host
2. **Traefik** — running with external network `traefik_proxy` and ACME resolver `letsencrypt`
3. **Environment** — `.env.prod` and `.env.pgbouncer.prod` configured (see below)
4. **PostgreSQL config** — `deploy/postgresql.conf` present on the host (referenced by compose)
5. **Firewall** — restrict host ports `5452` (Postgres) and `6380` (Redis) to trusted IPs if exposed

### Configure `.env.prod`

At minimum, set production values for:

```env
SECRET_KEY=<strong-random-key>
DEBUG=false
ALLOWED_HOSTS=*
PORT=8002

POSTGRES_DB=sortorium_db
POSTGRES_USER=sortorium_user
POSTGRES_PASSWORD=<secret>

DATABASE_URL=postgresql://sortorium_user:<password>@pgbouncer:6432/sortorium_db
DIRECT_DATABASE_URL=postgresql://sortorium_user:<password>@db:5432/sortorium_db
USE_PGBOUNCER=1

PUBLIC_DOMAIN=sortorium.com
TENANT_BASE_DOMAIN=sortorium.com
BACKEND_BASE_URL=https://sortorium.com
FRONTEND_BASE_URL=https://sortorium.com
CSRF_TRUSTED_ORIGINS=https://sortorium.com,https://*.sortorium.com
CORS_ALLOW_ALL_ORIGINS=false
CORS_ALLOWED_ORIGIN_REGEXES=^https://([a-z0-9-]+\.)?sortorium\.com$
```

URL-encode special characters in database passwords (e.g. `@` → `%40`).

### Deploy

```bash
cd Sortorium_Backend

# Build images
docker compose -f docker-compose.prod.yml build

# First deploy — run migrations (backend normally skips bootstrap in prod)
docker compose -f docker-compose.prod.yml run --rm \
  -e RUN_MIGRATIONS=1 \
  -e DIRECT_DATABASE_URL="${DIRECT_DATABASE_URL}" \
  backend /bin/sh -c "python manage.py migrate_schemas --shared --noinput && python manage.py migrate_schemas --noinput"

# Optional first-deploy setup
docker compose -f docker-compose.prod.yml run --rm backend python manage.py sync_features
docker compose -f docker-compose.prod.yml run --rm backend python manage.py seed_platform_roles
docker compose -f docker-compose.prod.yml run --rm backend python manage.py create_superadmin
docker compose -f docker-compose.prod.yml run --rm backend python manage.py collectstatic --noinput

# Start stack
docker compose -f docker-compose.prod.yml up -d
```

### Production services

| Service | Container | Role |
|---------|-----------|------|
| `backend` | `sortorium-backend` | ASGI app (port 8002, Traefik-routed) |
| `celery_worker` | `sortorium-celery-worker` | Background tasks |
| `celery_beat` | `sortorium-celery-beat` | Scheduled tasks |
| `pgbouncer` | `sortorium-pgbouncer` | Session pool to PostgreSQL |
| `db` | `sortorium-db` | PostgreSQL 18.4 |
| `redis` | `sortorium-redis` | Cache + Celery broker |

Traefik routes HTTPS traffic for `sortorium.com` and tenant subdomains to the backend on port **8002** for:

- `/api`, `/admin`, `/media`, `/static`
- `/ws` (WebSocket)
- `/iclock`, `/cdata`, `/getrequest`, `/devicecmd` (ADMS devices, HTTP)

Tenant **custom domains** are routed via separate Traefik routers with the `customdomains` cert resolver.

### Production host ports

| Port | Service | Notes |
|------|---------|-------|
| 8002 | Backend | Internal only (`expose`); Traefik publishes HTTPS |
| 5452 | PostgreSQL | Ops / backup access — firewall recommended |
| 6380 | Redis | Ops / debug — firewall recommended |

### Health checks

| Endpoint | Scope |
|----------|-------|
| `GET /api/v1/health/ready/` | Readiness (DB + cache) |
| `GET /api/v1/health/tenant/` | Tenant routing probe |

Production Docker healthcheck:

```bash
curl -fsS -H "Host: sortorium.com" -H "X-Forwarded-Proto: https" \
  http://127.0.0.1:8002/api/v1/health/ready/
```

## Common operations

### View logs

```bash
# Local
docker compose -f docker-compose.local.yml logs -f backend celery_worker

# Production
docker compose -f docker-compose.prod.yml logs -f backend celery_worker
```

### Run migrations

```bash
# Local — automatic on backend start, or manually:
docker compose -f docker-compose.local.yml exec backend \
  python manage.py migrate_schemas --shared --noinput
docker compose -f docker-compose.local.yml exec backend \
  python manage.py migrate_schemas --noinput

# Production — use DIRECT_DATABASE_URL (bypasses PgBouncer)
docker compose -f docker-compose.prod.yml run --rm \
  -e RUN_MIGRATIONS=1 backend \
  python manage.py migrate_schemas --shared --noinput
```

### Django shell

```bash
docker compose -f docker-compose.local.yml exec backend python manage.py shell
```

### Stop and remove

```bash
docker compose -f docker-compose.local.yml down
# Add -v to remove named volumes (destroys database data)
```

### Run tests

```bash
docker compose -f docker-compose.local.yml exec backend pytest
```

## Project layout

```
Sortorium_Backend/
├── apps/                  # Django apps (tenancy, access, branch, …)
├── config/                # Settings, URLs, ASGI/WSGI, health checks
├── shared/                # Shared views, middleware, pagination
├── scripts/
│   └── run-asgi-prod.sh   # Production Daphne entrypoint
├── docker-compose.local.yml
├── docker-compose.prod.yml
├── Dockerfile
├── entrypoint.sh          # Migrations, seeding, superadmin bootstrap
├── .env.example               # Main environment template
├── .env.local.celery.example  # Local Celery override template
├── .env.pgbouncer.prod.example  # Production PgBouncer template
├── .env.local                 # Local secrets (git-ignored)
├── .env.local.celery          # Local Celery secrets (git-ignored)
├── .env.prod                  # Production secrets (git-ignored)
└── .env.pgbouncer.prod        # PgBouncer secrets (git-ignored)
```

## Troubleshooting

**Backend cannot connect to PostgreSQL from the host**  
Use port `5452`, not `5432`, when connecting from outside Docker.

**Backend cannot connect to Redis from the host**  
Use port `6380`, not `6379`. Include the password: `redis-cli -a "$REDIS_PASSWORD" -p 6380 ping` or `redis://:PASSWORD@localhost:6380/0`.

**Redis startup warning about authentication**  
Ensure `REDIS_PASSWORD` is set in `.env.local` / `.env.prod` and matches the password embedded in `REDIS_*` / `CELERY_*` URLs, then recreate the container: `docker compose -f docker-compose.local.yml up -d --force-recreate redis`.

**Redis `Memory overcommit must be enabled` warning**  
`vm.overcommit_memory` is a host kernel setting (not per-container). Compose runs a one-shot `redis-sysctl-init` service before Redis to set it. If the warning persists (e.g. Docker Desktop without privileged init), run on the Linux/WSL host:

```bash
sudo sysctl vm.overcommit_memory=1
# persist: sudo ./scripts/redis-host-sysctl.sh
```

**Celery tasks not running**  
Check `celery_worker` logs and confirm `CELERY_BROKER_URL` resolves to `redis://:PASSWORD@redis:6379/0` inside the compose network.

**Production 502 / healthcheck failing**  
Confirm Daphne listens on port `8002`, `PUBLIC_DOMAIN` matches Traefik host rules, and Traefik targets `loadbalancer.server.port=8002`.

**PostgreSQL upgrade (17 → 18)**  
Back up data before upgrading. PG 18 requires the volume mount at `/var/lib/postgresql`. Migrate with `pg_dump` / restore or `pg_upgrade` — do not reuse an old `/data` volume path without migration.

**Traefik not routing**  
Ensure the `traefik_proxy` network exists (`docker network create traefik_proxy`) and the backend container is attached to it.
