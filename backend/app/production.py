"""Production migration and single-Uvicorn-process supervision."""
import asyncio
import os
import signal
import subprocess
import sys
import time
import urllib.request

def migrate():
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    from .config import get_settings
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg import AsyncConnection
    from psycopg.rows import dict_row
    async def checkpoints():
        async with await AsyncConnection.connect(
            get_settings().secret_value("database_url"),
            autocommit=True, prepare_threshold=0, row_factory=dict_row,
            connect_timeout=10,
        ) as connection:
            await connection.execute("SET search_path TO planner_internal")
            await AsyncPostgresSaver(connection).setup()
    asyncio.run(checkpoints())

def serve():
    command = [sys.executable, "-m", "uvicorn", "app.api.main:app",
               "--host", "0.0.0.0", "--port", "8000", "--workers", "1",
               "--proxy-headers", "--forwarded-allow-ips",
               os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1"),
               "--timeout-graceful-shutdown", "25"]
    child = subprocess.Popen(command)
    stopping = False
    def stop(*_):
        nonlocal stopping
        stopping = True
        if child.poll() is None:
            child.terminate()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    failures = 0
    next_probe = time.monotonic() + 60
    unhealthy = False
    while child.poll() is None and not stopping:
        if time.monotonic() >= next_probe:
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/health/ready", timeout=6) as response:
                    ready = response.status == 200
            except Exception:
                ready = False
            failures = 0 if ready else failures + 1
            next_probe = time.monotonic() + 15
            if failures >= 3:
                print("Readiness repeatedly failed; restarting backend.", flush=True)
                unhealthy = True
                stop()
        time.sleep(0.5)
    if child.poll() is None:
        try:
            child.wait(timeout=30)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
    return 1 if unhealthy else child.returncode

if __name__ == "__main__":
    if sys.argv[1:] == ["migrate"]:
        migrate()
    elif sys.argv[1:] == ["serve"]:
        sys.exit(serve())
    else:
        raise SystemExit("Expected: serve or migrate")
