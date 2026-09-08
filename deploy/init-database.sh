#!/bin/sh
set -eu
# Values are generated hex, and SQL receives the password via psql variables.
export APP_PASSWORD="$(cat /run/secrets/app_password)"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<'SQL'
\getenv app_password APP_PASSWORD
CREATE ROLE trip_app LOGIN PASSWORD :'app_password' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE DATABASE trip OWNER trip_app;
REVOKE ALL ON DATABASE trip FROM PUBLIC;
GRANT CONNECT ON DATABASE trip TO trip_app;
SQL
