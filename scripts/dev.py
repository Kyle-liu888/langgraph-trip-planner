#!/usr/bin/env python3
"""Local infrastructure manager. Python stdlib only; project runtimes stay in Docker."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
DEV = Path.home() / "dev"
CONFIG = DEV / "config"
INFRA = DEV / "infra" / "postgres"
BACKUPS = Path("/mnt/d/DevBackups/postgres")
LOCK = ROOT / "infra/postgres/images.lock.env"
IDENT = re.compile(r"^[a-z][a-z0-9_]{0,39}$")


def run(args, *, data=None, capture=False):
    return subprocess.run(args, input=data, check=True, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None).stdout


def write_private(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as file:
        file.write(content)


def identifier(value):
    if not IDENT.fullmatch(value):
        raise ValueError("Name must start with a-z and contain only a-z, 0-9, underscore (max 40).")
    return value


def envfile(path):
    return dict(line.split("=", 1) for line in path.read_text().splitlines()
                if line and not line.startswith("#") and "=" in line)


def docker_ready():
    run(["docker", "info", "--format", "{{.ServerVersion}}"], capture=True)


def pg_container():
    label = run(["docker", "inspect", "--format",
                 '{{index .Config.Labels "com.docker.compose.project"}}',
                 "local-dev-postgres"], capture=True).strip()
    if label != "local-infra":
        raise RuntimeError("Container name conflict; refusing to operate on another project's database.")


def psql(sql, database="postgres"):
    pg_container()
    # Secrets go through stdin, never command-line arguments or printed SQL errors.
    try:
        return run(["docker", "exec", "-i", "local-dev-postgres", "psql",
                    "-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-U", "dev_admin", "-d", database],
                   data=sql, capture=True).strip()
    except subprocess.CalledProcessError:
        raise RuntimeError("PostgreSQL operation failed. No SQL/credentials printed; existing data retained.") from None


def compose(kind, *args):
    config = INFRA / "compose.yaml" if kind == "infra" else ROOT / ".devcontainer/compose.yaml"
    return ["docker", "compose", "--env-file", str(LOCK),
            "--env-file", str(CONFIG / "infra.env"), "-f", str(config), *args]


def port_free(port):
    with socket.socket() as connection:
        try:
            connection.bind(("127.0.0.1", port))
        except OSError:
            raise RuntimeError(f"Port {port} is occupied. No process was stopped.") from None


def setup():
    CONFIG.mkdir(parents=True, exist_ok=True)
    CONFIG.chmod(0o700)
    INFRA.mkdir(parents=True, exist_ok=True)
    BACKUPS.mkdir(parents=True, exist_ok=True)
    admin = CONFIG / "postgres-admin-password"
    if not admin.exists():
        write_private(admin, secrets.token_hex(32))
    settings = CONFIG / "infra.env"
    if not settings.exists():
        write_private(settings, f"DEV_CONFIG_DIR={CONFIG}\n")
    target = INFRA / "compose.yaml"
    source = ROOT / "infra/postgres/compose.yaml"
    if target.exists() and target.read_bytes() != source.read_bytes():
        raise RuntimeError("Shared Compose already differs; review it manually instead of overwriting.")
    if not target.exists():
        shutil.copyfile(source, target)
    for name, example in (("trip-backend.env", "backend/.env.example"),
                          ("trip-frontend.env", "frontend/.env.example")):
        if not (CONFIG / name).exists():
            write_private(CONFIG / name, (ROOT / example).read_text())
    print("Configuration ready. Existing credentials were not changed.")


def pin_images():
    docker_ready()
    if LOCK.exists():
        raise RuntimeError("Image lock already exists; upgrades require explicit review.")
    tags = envfile(ROOT / "infra/postgres/images.example.env")
    pinned = {}
    for key, tag in tags.items():
        if not re.search(r":\d+\.\d+", tag):
            raise ValueError("Exact image version required.")
        run(["docker", "pull", tag])
        digests = json.loads(run(["docker", "image", "inspect", tag,
                                 "--format", "{{json .RepoDigests}}"], capture=True))
        if not digests or not re.search(r"@sha256:[a-f0-9]{64}$", digests[0]):
            raise RuntimeError("Registry did not return an immutable image digest.")
        pinned[key.replace("_TAG", "_IMAGE")] = tag + "@" + digests[0].split("@")[1]
    write_private(LOCK, "".join(f"{key}={value}\n" for key, value in pinned.items()))
    print("Version tags and registry digests locked. Review before committing the lock.")


def ensure_network():
    found = run(["docker", "network", "ls", "--filter", "name=^local-dev$",
                 "--format", "{{.Name}}"], capture=True).strip()
    if found:
        label = run(["docker", "network", "inspect", "local-dev", "--format",
                     '{{index .Labels "local.dev.managed"}}'], capture=True).strip()
        if label != "true":
            raise RuntimeError("Network local-dev already exists but is not managed by these scripts.")
    else:
        run(["docker", "network", "create", "--label", "local.dev.managed=true", "local-dev"])


def infra_up():
    docker_ready()
    if not LOCK.exists():
        raise RuntimeError("Run pin-images first. Floating database images are not allowed.")
    ensure_network()
    existing = run(["docker", "ps", "--filter", "name=^/local-dev-postgres$",
                    "--format", "{{.Names}}"], capture=True).strip()
    if not existing:
        port_free(15432)
    else:
        pg_container()
    run(compose("infra", "up", "-d", "--wait", "--wait-timeout", "90"))
    # This is a dedicated, newly created development cluster, not another server.
    psql("REVOKE CONNECT ON DATABASE postgres FROM PUBLIC;\n"
         "REVOKE CONNECT ON DATABASE template1 FROM PUBLIC;")


def new_database(name):
    name = identifier(name)
    role = identifier(name + "_app")
    record = CONFIG / f"db-{name}.json"
    if record.exists() or psql(f"SELECT 1 FROM pg_database WHERE datname='{name}';") or \
            psql(f"SELECT 1 FROM pg_roles WHERE rolname='{role}';"):
        raise RuntimeError("Database, role or credentials already exist; refusing to overwrite.")
    password = secrets.token_hex(32)
    value = {"database": name, "role": role, "password": password, "pending": True}
    write_private(record, json.dumps(value))
    psql(f'CREATE ROLE "{role}" LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD \'{password}\';')
    psql(f'CREATE DATABASE "{name}" OWNER "{role}";')
    psql(f'REVOKE ALL ON DATABASE "{name}" FROM PUBLIC; GRANT CONNECT, TEMPORARY ON DATABASE "{name}" TO "{role}";')
    psql('REVOKE CREATE ON SCHEMA public FROM PUBLIC;', name)
    value["pending"] = False
    record.write_text(json.dumps(value))
    write_private(CONFIG / f"{name}-database.env",
                  f"DATABASE_URL=postgresql://{role}:{password}@postgres:5432/{name}\n")
    print(f"Created database {name} and non-superuser role {role}; credentials are private.")
    return value


def records():
    result = []
    for file in sorted(CONFIG.glob("db-*.json")):
        value = json.loads(file.read_text())
        if value.get("pending"):
            raise RuntimeError(f"Database {value['database']} provisioning is incomplete; inspect before continuing.")
        identifier(value["database"])
        result.append(value)
    return result


def backup_all():
    pg_container()
    BACKUPS.mkdir(parents=True, exist_ok=True)
    for value in records():
        name = value["database"]
        directory = BACKUPS / name
        directory.mkdir(exist_ok=True)
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        temporary = directory / f"{stamp}.partial"
        final = directory / f"{stamp}.dump"
        with temporary.open("xb") as file:
            subprocess.run(["docker", "exec", "local-dev-postgres", "pg_dump",
                            "-U", "dev_admin", "-d", name, "--format=custom",
                            "--no-owner", "--no-acl"], stdout=file, check=True)
        with temporary.open("rb") as file:
            subprocess.run(["docker", "exec", "-i", "local-dev-postgres", "pg_restore", "--list"],
                           stdin=file, stdout=subprocess.DEVNULL, check=True)
        temporary.rename(final)
        final.with_suffix(".sha256").write_text(hashlib.sha256(final.read_bytes()).hexdigest())
        # Rotate only this validated database's completed backups, after success.
        for old in sorted(directory.glob("*.dump"), reverse=True)[14:]:
            if old.parent.resolve() != directory.resolve() or directory.parent.resolve() != BACKUPS.resolve():
                raise RuntimeError("Unsafe backup path.")
            old.unlink()
            old.with_suffix(".sha256").unlink(missing_ok=True)
        print(f"Backup verified: {final} (keep newest 14 per database)")
    backup_configuration()


def backup_configuration():
    directory = BACKUPS.parent / "config"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = directory / f"{stamp}.tar.gz.partial"
    with tarfile.open(path, "x:gz") as archive:
        for source in sorted(CONFIG.iterdir()):
            if source.is_file() and not source.is_symlink():
                archive.add(source, arcname=source.name)
        if LOCK.exists():
            archive.add(LOCK, arcname="images.lock.env")
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            if member.isfile():
                archive.extractfile(member).read()  # Validate compression without extracting secrets.
    path.rename(directory / f"{stamp}.tar.gz")
    for old in sorted(directory.glob("*.tar.gz"), reverse=True)[14:]:
        if old.parent.resolve() != directory.resolve():
            raise RuntimeError("Unsafe configuration backup path.")
        old.unlink()
    print("Private configuration archive verified. Keep the D-drive backup directory access-restricted.")


def restore(source, target):
    source = Path(source).resolve(strict=True)
    if source.suffix != ".dump":
        raise ValueError("Use a custom-format .dump backup.")
    checksum = source.with_suffix(".sha256")
    if not checksum.exists() or checksum.read_text().strip() != hashlib.sha256(source.read_bytes()).hexdigest():
        raise RuntimeError("Backup checksum missing or mismatched.")
    value = new_database(target)  # Always a new DB/role; never overwrite source.
    with source.open("rb") as file:
        subprocess.run(["docker", "exec", "-i", "local-dev-postgres", "pg_restore",
                        "-U", "dev_admin", "-d", value["database"], "--role", value["role"],
                        "--no-owner", "--no-acl", "--exit-on-error", "--single-transaction"],
                       stdin=file, check=True)
    psql("REVOKE CREATE ON SCHEMA public FROM PUBLIC;", target)
    if psql("SELECT 1 FROM pg_namespace WHERE nspname='planner_internal';", target):
        psql("REVOKE ALL ON SCHEMA planner_internal FROM PUBLIC;", target)
    print(f"Restored into NEW database {target}. Original database untouched; verify app data before switching.")


def project_up():
    infra_up()
    if not (CONFIG / "trip-database.env").exists():
        new_database("trip")
    existing = run(compose("project", "ps", "--status", "running", "-q"), capture=True).strip()
    if not existing:
        for port in (5173, 8000):
            port_free(port)
    # Dev Containers loads the same Compose interpolation without global shell variables.
    dev_env = ROOT / ".devcontainer/.env"
    content = LOCK.read_text() + (CONFIG / "infra.env").read_text()
    if dev_env.exists() and dev_env.read_text() != content:
        raise RuntimeError("Dev Container local environment differs; review before updating.")
    if not dev_env.exists():
        write_private(dev_env, content)
    if existing:
        print("Workspace is already running; no rebuild or dependency reinstall was performed.")
        return
    run(compose("project", "up", "-d", "--build"))
    run(compose("project", "exec", "-T", "workspace", "bash", "scripts/container-setup.sh"))
    print("Open this Linux folder in VS Code, then Reopen in Container. Run migration/backend/frontend tasks separately.")


def status():
    docker_ready()
    run(["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"])
    for value in records():
        name = value["database"]
        if psql("SELECT to_regclass('public.trips') IS NOT NULL;", name) == "t":
            active = psql("SELECT count(*) FROM trips WHERE status IN ('queued','running');", name)
            print(f"{name}: active planner jobs={active}")


def verify_postgres(name=None):
    if name is None:
        name = "test_trip_" + dt.datetime.now().strftime("%Y%m%d%H%M%S")
        value = new_database(name)
        other = new_database(name + "_other")
    else:
        identifier(name)
        if not name.startswith("test_"):
            raise ValueError("Only dedicated test_* databases may be reused for acceptance.")
        registered = {item["database"]: item for item in records()}
        value, other = registered[name], registered[name + "_other"]
    code = """
import json, os, sys
import psycopg
from alembic import command
from alembic.config import Config
data = json.load(sys.stdin)
url = data['url']
os.environ['DATABASE_URL'] = url
os.environ['TEST_DATABASE_URL'] = url
os.chdir('/workspace/backend')
sys.path.insert(0, '/workspace/backend')
command.upgrade(Config('alembic.ini'), 'head')
try:
    with psycopg.connect(url.rsplit('/', 1)[0] + '/' + data['other']):
        raise AssertionError('Cross-project access unexpectedly allowed')
except psycopg.OperationalError as error:
    # Connect-time FATAL can be OperationalError rather than a SQL statement subclass.
    if 'permission denied for database' not in str(error):
        raise RuntimeError('Cross-project probe failed for an unexpected reason') from None
with psycopg.connect(url) as db:
    flags = db.execute('SELECT rolsuper, rolcreatedb, rolcreaterole, rolbypassrls FROM pg_roles WHERE rolname=current_user').fetchone()
    assert flags == (False, False, False, False)
import pytest
raise SystemExit(pytest.main(['tests/test_local_postgres.py', '-q']))
"""
    url = f"postgresql://{value['role']}:{value['password']}@postgres:5432/{name}"
    run(compose("project", "exec", "-T", "workspace", "/workspace/backend/.venv/bin/python", "-c", code),
        data=json.dumps({"url": url, "other": other["database"]}))
    print(f"PostgreSQL acceptance databases retained: {name}, {other['database']}. No real APIs called.")


def stop_trip():
    running = run(compose('project', 'ps', '--status', 'running', '-q'), capture=True).strip()
    if running:
        run(compose('project', 'exec', '-T', 'workspace', 'python', '/workspace/scripts/stop_services.py'))
    run(compose('project', 'stop'))


def stop_all():
    status()
    if input("This stops ALL Docker containers. Type STOP ALL to back up then stop: ") != "STOP ALL":
        raise RuntimeError("Cancelled; nothing stopped.")
    backup_all()  # Any failure prevents all subsequent shutdown steps.
    stop_trip()
    ids = run(["docker", "ps", "-q"], capture=True).split()
    # Stop apps first, while PostgreSQL is still available to persist interruptions.
    database_id = run(["docker", "inspect", "--format", "{{.Id}}", "local-dev-postgres"], capture=True).strip()
    app_ids = [item for item in ids if not database_id.startswith(item)]
    if app_ids:
        run(["docker", "stop", "--time", "45", *app_ids])
    backup_all()  # Capture the final interrupted states too, before stopping storage.
    run(compose("infra", "stop"))
    print("Docker containers stopped; volumes retained. WSL shutdown must be confirmed from Windows.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["setup", "pin-images", "infra-up", "new-db", "backup",
                        "restore", "start", "stop-trip", "stop-containers", "status", "verify-postgres"])
    parser.add_argument("arguments", nargs="*")
    args = parser.parse_args()
    actions = {"setup": setup, "pin-images": pin_images, "infra-up": infra_up, "new-db": new_database,
               "backup": backup_all, "restore": restore, "start": project_up,
               "stop-trip": stop_trip,
               "stop-containers": stop_all, "status": status, "verify-postgres": verify_postgres}
    try:
        actions[args.action](*args.arguments)
    except (subprocess.CalledProcessError, OSError, ValueError, RuntimeError, TypeError) as error:
        # Do not dump subprocess input, environment, SQL or private credentials.
        print(str(error) if not isinstance(error, subprocess.CalledProcessError)
              else "External command failed; no credentials printed. No cleanup attempted.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
