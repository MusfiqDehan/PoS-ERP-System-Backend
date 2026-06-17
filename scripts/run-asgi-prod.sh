#!/bin/sh
set -e

PORT="${PORT:-8002}"
BIND="${ASGI_BIND:-0.0.0.0}"

exec daphne -b "${BIND}" -p "${PORT}" config.asgi:application
