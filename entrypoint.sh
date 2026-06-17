#!/bin/sh
set -e

apply_direct_database_url() {
    if [ -n "${DIRECT_DATABASE_URL:-}" ]; then
        echo "Using DIRECT_DATABASE_URL for bootstrap/migrations."
        export DATABASE_URL="${DIRECT_DATABASE_URL}"
        export USE_PGBOUNCER=0
        export DB_CONN_MAX_AGE=0
    fi
}

if [ "${SKIP_DB_BOOTSTRAP:-0}" = "1" ]; then
    if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
        apply_direct_database_url
        echo "Running shared schema migrations..."
        python manage.py migrate_schemas --shared --noinput
        echo "Running tenant schema migrations..."
        python manage.py migrate_schemas --noinput
    else
        echo "Skipping DB bootstrap/migrations (SKIP_DB_BOOTSTRAP=1)."
    fi
    exec "$@"
fi

apply_direct_database_url

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Running shared schema migrations..."
python manage.py migrate_schemas --shared --noinput

echo "Running tenant schema migrations..."
python manage.py migrate_schemas --noinput

echo "Syncing feature registry..."
python manage.py sync_features || true

echo "Seeding platform roles..."
python manage.py seed_platform_roles || true

echo "Ensuring superadmin account exists..."
python manage.py create_superadmin || true

echo "Starting server..."
exec "$@"
