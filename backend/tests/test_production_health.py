"""Production readiness must detect storage loss without spending API credits."""
import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


def test_readiness_detects_checkpoint_connection_loss_and_stops_admission(monkeypatch):
    from app.api.main import app
    class Connection:
        def __init__(self):
            self.failed = False
        async def execute(self, _):
            if self.failed:
                raise ConnectionError("checkpoint disconnected")
    business, checkpoint = Connection(), Connection()
    class Engine:
        @asynccontextmanager
        async def connect(self):
            yield business
    runs = SimpleNamespace(closing=False)
    monkeypatch.setattr(app.state, "run_manager", runs, raising=False)
    monkeypatch.setattr(app.state, "storage_engine", Engine(), raising=False)
    monkeypatch.setattr(app.state, "checkpoint_saver",
                        SimpleNamespace(conn=checkpoint, lock=asyncio.Lock()), raising=False)
    client = TestClient(app)
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200
    checkpoint.failed = True
    assert client.get("/health/ready").status_code == 503
    assert runs.closing is True
    assert client.get("/health/live").status_code == 200


def test_missing_database_fails_startup_only_in_production(monkeypatch):
    from app.api.main import app, settings
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr(settings, "log_file_enabled", False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        with TestClient(app):
            pass
