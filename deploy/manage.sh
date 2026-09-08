#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
compose() {
    docker compose --env-file infra/postgres/images.lock.env --env-file deploy/.env -f compose.prod.yaml "$@"
}
case "${1:-status}" in
    build) compose build backend web ;;
    up) compose up -d --no-build --wait --wait-timeout 120 ;;
    status) compose ps ;;
    logs) compose logs --tail=100 "${2:-backend}" ;;
    backup)
        umask 077
        mkdir -p deploy/backups
        target="deploy/backups/trip-$(date -u +%Y%m%dT%H%M%SZ).dump"
        compose exec -T postgres pg_dump -U trip_admin -d trip -Fc > "$target.partial"
        mv "$target.partial" "$target"
        printf '%s\n' "$target"
        ;;
    *) echo "Usage: sh deploy/manage.sh build|up|status|logs [service]|backup"; exit 2 ;;
esac
