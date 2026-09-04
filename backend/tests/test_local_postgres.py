"""Explicit opt-in real PostgreSQL acceptance; requires a dedicated test_* database."""
import asyncio
import os
from types import SimpleNamespace
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from app.api.routes import auth, trips
from app.database import create_database
from app.graph import build_planner_graph
from app.services.run_manager import RunManager
from test_local_auth import bootstrap, exercise_auth, ORIGIN
from test_planner_graph import make_request, make_runtime, valid_plan_json


def test_real_postgres_auth_history_and_checkpoint_reopen():
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("Run scripts/dev.py verify-postgres; real PostgreSQL has not been supplied.")
    if not urlsplit(url).path.lstrip("/").startswith("test_"):
        pytest.fail("Refusing to run against a non-test database")

    async def scenario():
        engine, sessions = create_database(url)
        try:
            await exercise_auth(sessions)
            async with await AsyncConnection.connect(url, autocommit=True, prepare_threshold=0,
                                                     row_factory=dict_row) as connection:
                await connection.execute("SET search_path TO planner_internal")
                saver = AsyncPostgresSaver(connection)
                await saver.setup()
                runtime = make_runtime([valid_plan_json()])
                planner = SimpleNamespace(graph=build_planner_graph(saver), runtime=runtime)
                runs = RunManager(sessions, planner, saver, runtime.settings)
                app = FastAPI()
                app.state.auth_sessions, app.state.run_manager = sessions, runs
                app.include_router(auth.router, prefix="/api")
                app.include_router(trips.router, prefix="/api")
                transport = httpx.ASGITransport(app)
                try:
                    async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
                        headers = await bootstrap(client)
                        registered = await client.post("/api/auth/register", headers=headers,
                            json={"email": f"{uuid4()}@example.test", "password": "acceptance-password"})
                        assert registered.status_code == 201
                        owner = registered.json()["user"]["id"]
                        headers["X-CSRF-Token"] = registered.json()["csrf_token"]
                        headers["X-Idempotency-Key"] = str(uuid4())
                        # Persist a real checkpoint before model generation; emulate process interruption.
                        spawn = runs.spawn
                        runs.spawn = lambda *args: None
                        created = await client.post("/api/trips", headers=headers, json=make_request().model_dump(mode="json"))
                        assert created.status_code == 202
                        trip_id = created.json()["id"]
                        owner_cookies = dict(client.cookies)
                        config = {"configurable": {"thread_id": trip_id}}
                        await planner.graph.ainvoke({"request": make_request().model_dump(mode="json")},
                            config=config, context=runtime, interrupt_before=["generate_candidate"])
                        await runs.close()
                        runs.spawn = spawn
                    # A new connection/saver must recover the previous node state.
                finally:
                    await runs.close()
            async with await AsyncConnection.connect(url, autocommit=True, prepare_threshold=0,
                                                     row_factory=dict_row) as connection:
                await connection.execute("SET search_path TO planner_internal")
                saver = AsyncPostgresSaver(connection)
                runtime = make_runtime([valid_plan_json()])
                runs = RunManager(sessions, SimpleNamespace(graph=build_planner_graph(saver), runtime=runtime),
                                  saver, runtime.settings)
                try:
                    assert (await runs.planner.graph.aget_state(config)).next == ("generate_candidate",)
                    await runs.recover_interrupted()
                    await runs.resume(trip_id, owner)
                    await runs.tasks[trip_id]
                    async with sessions() as db:
                        result = await runs.owned(db, trip_id, owner)
                        assert result.status == "completed" and result.plan
                    app.state.run_manager = runs
                    async with httpx.AsyncClient(transport=transport, base_url=ORIGIN, cookies=owner_cookies) as client:
                        record = (await client.get(f"/api/trips/{trip_id}")).json()
                        assert record["status"] == "completed"
                        saved = await client.put(f"/api/trips/{trip_id}/plan", headers=headers,
                            json={"plan": record["plan"], "revision": record["revision"]})
                        assert saved.status_code == 200
                        assert saved.json()["revision"] == record["revision"] + 1
                        stream = await client.get(f"/api/trips/{trip_id}/events")
                        assert "event: stream.closed" in stream.text
                        ids = [int(line[4:]) for line in stream.text.splitlines() if line.startswith("id: ")]
                        assert len(ids) > 1 and ids == sorted(set(ids))
                        replay = await client.get(f"/api/trips/{trip_id}/events", headers={"Last-Event-ID": str(ids[-2])})
                        assert f"id: {ids[-1]}\n" in replay.text and f"id: {ids[0]}\n" not in replay.text
                    async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
                        headers = await bootstrap(client)
                        # Credentials from the registration above remain only in this test process.
                        # Second account cannot read or subscribe to the original owner's trip.
                        result = await client.post("/api/auth/register", headers=headers,
                            json={"email": f"{uuid4()}@example.test", "password": "another-password"})
                        assert result.status_code == 201
                        assert (await client.get(f"/api/trips/{trip_id}")).status_code == 404
                        assert (await client.get(f"/api/trips/{trip_id}/events")).status_code == 404
                finally:
                    await runs.close()
        finally:
            await engine.dispose()
    asyncio.run(scenario())
