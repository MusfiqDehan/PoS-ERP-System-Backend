#!/usr/bin/env bash
# Blue-green zero-downtime production deploy for Sortorium backend.
# Run on the VPS from the repository root (VPS_DEPLOY_PATH).
set -euo pipefail

IMAGE_TAG="${IMAGE_TAG:-latest}"
LIVE_CONTAINER="sortorium-backend"
CANDIDATE_CONTAINER="sortorium-backend-candidate"
COMPOSE=(docker compose -f docker-compose.prod.yml)
COMPOSE_DEPLOY=(docker compose -f docker-compose.prod.yml -f docker-compose.deploy.yml)
SMOKE_URL="${SMOKE_URL:-https://sortorium.com/api/v1/health/ready/}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-300}"
DRAINED=0

log() { printf '[deploy] %s\n' "$*"; }
die() { printf '[deploy] ERROR: %s\n' "$*" >&2; exit 1; }

cleanup_candidate() {
  log "Removing candidate container (if any)..."
  IMAGE_TAG="$IMAGE_TAG" "${COMPOSE_DEPLOY[@]}" rm -sf backend_candidate >/dev/null 2>&1 || true
  docker rm -f "$CANDIDATE_CONTAINER" >/dev/null 2>&1 || true
}

on_error() {
  local exit_code=$?
  if [[ "$DRAINED" -eq 0 ]]; then
    log "Deploy failed before live drain — live container should still be serving."
    cleanup_candidate
  else
    log "Deploy failed after live drain — investigate canonical backend immediately."
  fi
  exit "$exit_code"
}
trap on_error ERR

wait_container_healthy() {
  local name=$1
  local deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))
  log "Waiting for $name to become healthy..."
  while (( SECONDS < deadline )); do
    local status
    status="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$name" 2>/dev/null || echo missing)"
    if [[ "$status" == "healthy" ]]; then
      log "$name is healthy."
      return 0
    fi
    if [[ "$status" == "missing" ]]; then
      die "Container $name not found."
    fi
    sleep 5
  done
  die "Timed out waiting for $name to become healthy."
}

smoke_check() {
  log "HTTPS smoke check: $SMOKE_URL"
  curl -fsS --retry 5 --retry-delay 3 --retry-all-errors "$SMOKE_URL" >/dev/null
}

export IMAGE_TAG

finalize_deploy_tree() {
  # CI syncs this directory via rsync (see .github/workflows/production.yml).
  # rsync excludes .git/, so an old clone leaves HEAD behind while files on disk
  # match GitHub — git status then shows thousands of phantom changes.
  if [[ -d .git ]]; then
    log "Removing stale .git metadata (deploy tree is rsync-managed, not git-managed)."
    rm -rf .git
  fi
  printf '%s\n' "${IMAGE_TAG}" > .deploy-revision
}

finalize_deploy_tree

log "Phase 1: build backend image (tag=$IMAGE_TAG) while live serves..."
IMAGE_TAG="$IMAGE_TAG" "${COMPOSE[@]}" build backend

log "Phase 2: run migrations (live still serving)..."
IMAGE_TAG="$IMAGE_TAG" "${COMPOSE[@]}" run --rm --no-deps \
  -e RUN_MIGRATIONS=1 \
  backend /bin/sh -c \
  'python manage.py migrate_schemas --shared --noinput && python manage.py migrate_schemas --noinput'

log "Phase 3: start backend candidate alongside live..."
IMAGE_TAG="$IMAGE_TAG" "${COMPOSE_DEPLOY[@]}" up -d --no-deps backend_candidate

log "Phase 4: wait for candidate health..."
wait_container_healthy "$CANDIDATE_CONTAINER"

log "Phase 5: external smoke check (Traefik load-balances live + candidate)..."
smoke_check

log "Phase 6: graceful drain of live backend..."
DRAINED=1
docker stop -t 30 "$LIVE_CONTAINER"

log "Phase 7: promote canonical backend with image tag $IMAGE_TAG..."
IMAGE_TAG="$IMAGE_TAG" "${COMPOSE[@]}" up -d --no-deps backend

log "Phase 8: wait for canonical backend..."
wait_container_healthy "$LIVE_CONTAINER"

log "Phase 9: remove candidate..."
cleanup_candidate

log "Phase 10: rolling Celery worker update..."
IMAGE_TAG="$IMAGE_TAG" "${COMPOSE[@]}" up -d --no-deps celery_worker celery_beat

log "Phase 11: final smoke check..."
smoke_check

trap - ERR
log "Backend deploy complete (image tag=$IMAGE_TAG)."
