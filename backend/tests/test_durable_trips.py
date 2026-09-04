"""Offline integration tests: real graph + real durable SQLite test adapters, no paid APIs."""
import asyncio
import json
import time
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlalchemy import select, update

from app.api.routes.trips import router, manager, save_plan, SavePlan
from app.auth import User, require_user
from app.database import Base, Trip, TripEvent, create_database
from app.graph import build_planner_graph
from app.services.run_manager import RunManager
from test_planner_graph import make_request, make_runtime, valid_plan_json

OWNER, OTHER = str(uuid4()), str(uuid4())


@asynccontextmanager
async def system(tmp_path, responses=None):
    engine, sessions = create_database(f"sqlite+aiosqlite:///{(tmp_path / 'app.db').as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with AsyncSqliteSaver.from_conn_string(str(tmp_path / 'graph.db')) as saver:
        runtime = make_runtime(responses or [valid_plan_json()])
        planner = SimpleNamespace(graph=build_planner_graph(saver), runtime=runtime)
        runs = RunManager(sessions, planner, saver, runtime.settings)
        try:
            yield runs
        finally:
            await runs.close()
    await engine.dispose()


async def wait_run(runs, trip_id):
    if task := runs.tasks.get(trip_id):
        await task
    async with runs.sessions() as session:
        return await runs.owned(session, trip_id, OWNER)


def test_create_idempotency_events_and_quota_survives_delete(tmp_path):
    async def scenario():
        async with system(tmp_path) as runs:
            runs.settings.daily_trip_limit = 1
            key = str(uuid4())
            created = await runs.create(OWNER, make_request(), key)
            same = await runs.create(OWNER, make_request(), key)
            assert created['id'] == same['id']
            completed = await wait_run(runs, created['id'])
            assert completed.status == 'completed'
            assert completed.plan['city'] == '北京'
            async with runs.sessions() as session:
                events = (await session.scalars(select(TripEvent).order_by(TripEvent.id))).all()
                kinds = [event.payload['type'] for event in events]
                assert kinds[0] == 'run.queued' and kinds[-1] == 'run.completed'
                assert 'model.started' in kinds and 'model.completed' in kinds
                starts = [event.payload['node'] for event in events if event.payload['type'] == 'node.started']
                assert starts == ['collect_context', 'build_prompt', 'generate_candidate', 'validate_candidate', 'select_best_candidate']
                serialized = json.dumps([event.payload for event in events])
                assert 'planner_query' not in serialized and 'access_token' not in serialized
                with pytest.raises(HTTPException) as forbidden:
                    await runs.owned(session, created['id'], OTHER)
                assert forbidden.value.status_code == 404
            changed = make_request().model_copy(update={'city': '上海'})
            with pytest.raises(HTTPException) as conflict:
                await runs.create(OWNER, changed, key)
            assert conflict.value.status_code == 409
            await runs.remove(created['id'], OWNER)
            assert not (await runs.planner.graph.aget_state({'configurable': {'thread_id': created['id']}})).values
            with pytest.raises(HTTPException) as limit:
                await runs.create(OWNER, make_request(), str(uuid4()))
            assert limit.value.status_code == 429
    asyncio.run(scenario())


def test_restart_resume_skips_completed_nodes_and_uses_same_thread(tmp_path):
    async def scenario():
        async with system(tmp_path) as runs:
            spawn = runs.spawn
            runs.spawn = lambda *args: None
            created = await runs.create(OWNER, make_request(), str(uuid4()))
            config = {'configurable': {'thread_id': created['id']}}
            await runs.planner.graph.ainvoke({'request': make_request().model_dump(mode='json')},
                config=config, context=runs.planner.runtime, interrupt_before=['generate_candidate'])
            assert (await runs.planner.graph.aget_state(config)).next == ('generate_candidate',)
            runs.spawn = spawn
        # Reopen the files, not merely an in-memory saver: simulate a new process.
        async with system(tmp_path) as restarted:
            await restarted.recover_interrupted()
            async with restarted.sessions() as session:
                record = await restarted.owned(session, created['id'], OWNER)
                assert record.status == 'interrupted'
            resumed = await restarted.resume(created['id'], OWNER)
            assert resumed['run_id'] != created['run_id']
            assert (await wait_run(restarted, created['id'])).status == 'completed'
            async with restarted.sessions() as session:
                events = (await session.scalars(select(TripEvent).where(TripEvent.run_id == resumed['run_id']))).all()
                starts = [event.payload.get('node') for event in events if event.payload['type'] == 'node.started']
                assert starts[0] == 'generate_candidate'
                assert 'collect_context' not in starts and 'build_prompt' not in starts
    asyncio.run(scenario())


def test_completed_checkpoint_recovery_does_not_call_model(tmp_path):
    async def scenario():
        async with system(tmp_path) as runs:
            spawn = runs.spawn
            runs.spawn = lambda *args: None
            created = await runs.create(OWNER, make_request(), str(uuid4()))
            await runs.planner.graph.ainvoke({'request': make_request().model_dump(mode='json')},
                config={'configurable': {'thread_id': created['id']}}, context=runs.planner.runtime)
            await runs.recover_interrupted()
            runs.spawn = spawn
            resumed = await runs.resume(created['id'], OWNER)
            assert (await wait_run(runs, created['id'])).status == 'completed'
            async with runs.sessions() as session:
                events = (await session.scalars(select(TripEvent).where(TripEvent.run_id == resumed['run_id']))).all()
                assert not any(event.payload['type'] == 'model.started' for event in events)
    asyncio.run(scenario())


def test_fallback_and_revision_conflict(tmp_path):
    async def scenario():
        async with system(tmp_path, ['invalid']) as runs:
            created = await runs.create(OWNER, make_request(), str(uuid4()))
            record = await wait_run(runs, created['id'])
            assert record.status == 'fallback'
            assert 'invalid' not in record.message
            user = User(OWNER, int(time.time()) + 3600)
            saved = await save_plan(UUID(record.id), SavePlan(plan=record.plan, revision=1), user, runs)
            assert saved['revision'] == 2
            with pytest.raises(HTTPException) as conflict:
                await save_plan(UUID(record.id), SavePlan(plan=record.plan, revision=1), user, runs)
            assert conflict.value.status_code == 409
    asyncio.run(scenario())


def test_authenticated_api_history_sse_replay_and_expiry(tmp_path):
    async def scenario():
        async with system(tmp_path) as runs:
            app = FastAPI()
            app.include_router(router, prefix='/api')
            app.dependency_overrides[manager] = lambda: runs
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url='http://test') as client:
                assert (await client.get('/api/trips')).status_code == 401
                app.dependency_overrides[require_user] = lambda: User(OWNER, int(time.time()) + 3600)
                response = await client.post('/api/trips', json=make_request().model_dump(mode='json'),
                                             headers={'X-Idempotency-Key': str(uuid4())})
                assert response.status_code == 202
                trip_id = response.json()['id']
                await wait_run(runs, trip_id)
                listing = await client.get('/api/trips')
                assert listing.json()['items'][0]['id'] == trip_id
                stream = await client.get(f'/api/trips/{trip_id}/events')
                assert stream.headers['content-type'].startswith('text/event-stream')
                assert 'event: stream.closed' in stream.text
                ids = [int(line[4:]) for line in stream.text.splitlines() if line.startswith('id: ')]
                assert ids == sorted(set(ids))
                replay = await client.get(f'/api/trips/{trip_id}/events', headers={'Last-Event-ID': str(ids[-2])})
                assert f'id: {ids[-1]}\n' in replay.text and f'id: {ids[0]}\n' not in replay.text
                app.dependency_overrides[require_user] = lambda: User(OWNER, 0)
                assert 'session.expired' in (await client.get(f'/api/trips/{trip_id}/events')).text
                app.dependency_overrides[require_user] = lambda: User(OTHER, int(time.time()) + 3600)
                assert (await client.get('/api/trips')).json()['items'] == []
                for method, path in [('GET', ''), ('GET', '/events'), ('POST', '/resume'), ('DELETE', '')]:
                    assert (await client.request(method, f'/api/trips/{trip_id}{path}')).status_code == 404
    asyncio.run(scenario())


def test_one_active_job_per_user_and_shutdown_cancellation(tmp_path):
    async def scenario():
        async with system(tmp_path) as runs:
            await runs.slots.acquire()
            await runs.slots.acquire()
            created = await runs.create(OWNER, make_request(), str(uuid4()))
            await asyncio.sleep(0)  # let the task enter its cancellable semaphore wait
            with pytest.raises(HTTPException) as conflict:
                await runs.create(OWNER, make_request(), str(uuid4()))
            assert conflict.value.status_code == 409
            with pytest.raises(HTTPException) as conflict:
                await runs.remove(created['id'], OWNER)
            assert conflict.value.status_code == 409
            await runs.close()
            async with runs.sessions() as session:
                assert (await runs.owned(session, created['id'], OWNER)).status == 'interrupted'
    asyncio.run(scenario())
