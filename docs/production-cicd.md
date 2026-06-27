# Production CI/CD — Sortorium Backend

Gated GitHub Actions pipeline for the `production` branch with **blue-green zero-downtime** deploy to the VPS.

**Repository:** `GeekSSort/Sortorium_Backend`  
**Workflow:** `.github/workflows/production.yml`

## Pipeline overview

```
PR → production     →  ci only (ruff, black, mypy, pytest, migration drift)
push → production   →  ci  →  deploy (blue-green on VPS)
```

Deploy uses `scripts/deploy/production.sh` over SSH. The live `sortorium-backend` container keeps serving until `sortorium-backend-candidate` is healthy behind Traefik.

## Required GitHub secrets

Configure in **Settings → Secrets and variables → Actions**:

| Secret | Example | Purpose |
|--------|---------|---------|
| `VPS_HOST` | `203.0.113.10` | VPS IP or hostname |
| `VPS_USER` | `deploy` | SSH user |
| `VPS_SSH_KEY` | ed25519 private key | SSH authentication |
| `VPS_DEPLOY_PATH` | `/opt/sortorium/backend` | Deploy directory on VPS (plain folder; not a git working copy) |

CI **rsyncs** the GitHub checkout to `VPS_DEPLOY_PATH` (the VPS does not `git pull`). `.env.prod` and `.env.pgbouncer.prod` live only on the server and are never overwritten. After each deploy, `.deploy-revision` records the deployed commit SHA.

### Why not git on the VPS?

If the deploy path was originally `git clone`d, rsync updates files on disk but **excludes `.git/`**, so `git status` compares new files against an old `HEAD` and shows thousands of phantom changes. The deploy script removes any leftover `.git` directory on each run. **Do not run `git pull` on the server** — use GitHub Actions or re-run the workflow.

## VPS prerequisites

1. Docker + Compose plugin installed
2. External `traefik_proxy` network exists
3. `.env.prod` and `.env.pgbouncer.prod` configured
4. Stack initially started: `docker compose -f docker-compose.prod.yml up -d`
5. Deploy user in `docker` group

## Blue-green deploy phases

| Phase | Action | Live API up? |
|-------|--------|--------------|
| 1 | Build image (`IMAGE_TAG` = git SHA) | Yes |
| 2 | Run `migrate_schemas` one-off | Yes |
| 3 | Start `backend_candidate` | Yes (both serve via Traefik) |
| 4–5 | Candidate health + HTTPS smoke | Yes |
| 6 | Graceful stop live (`stop_grace_period: 30s`) | Candidate serves 100% |
| 7–8 | Promote canonical `backend` | Yes |
| 9 | Remove candidate | Yes |
| 10 | Recreate Celery worker/beat | API up; queue may pause briefly |
| 11 | Final smoke check | Yes |

**Failed deploy before Phase 6:** candidate is removed; live container untouched.

### Compose files

- `docker-compose.prod.yml` — production stack
- `docker-compose.deploy.yml` — `backend_candidate` overlay (Traefik routers suffixed `-candidate`, same `backend` service)

### Manual deploy

```bash
cd /opt/sortorium/backend   # VPS_DEPLOY_PATH
# Re-run the GitHub Actions workflow, or rsync from a local checkout.
# Check deployed SHA:
cat .deploy-revision
```

## Migration compatibility (zero downtime)

Migrations run while the **old** backend still serves traffic. Use expand-only / backward-compatible migrations:

- Add nullable columns and new tables
- Avoid destructive changes, column renames, or NOT NULL without defaults in the same release

Breaking migrations require a planned maintenance window.

## Rollback

Re-run the GitHub Actions workflow on an older commit on `production`, or use **workflow_dispatch** after resetting the branch. The deploy path is rsync-managed — do not use `git reset` on the server.

If a deploy failed before live drain, the previous container may still be running — verify with `docker ps`.

## Post-setup validation (manual)

### Configure secrets (one-time)

Add all four secrets to the GitHub repo before the first `production` merge.

### Zero-downtime curl loop during deploy

On a machine with network access to production, run during a deploy:

```bash
while curl -sf https://sortorium.com/api/v1/health/ready/; do sleep 1; done
```

Expect no failed curls for the duration of the deploy.

### Failed-deploy safety test

1. Temporarily break candidate healthcheck (e.g. wrong command in deploy overlay on a test branch)
2. Run deploy script
3. Confirm deploy aborts and `sortorium-backend` is still healthy

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Deploy SSH fails | `VPS_HOST`, key, firewall port 22 |
| Candidate never healthy | `docker logs sortorium-backend-candidate` |
| Traefik 502 after cutover | `docker inspect` health; Traefik labels on candidate |
| Migration failure | DB logs; deploy aborts before candidate start |
