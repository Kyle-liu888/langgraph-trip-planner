"""An already-open stream observes durable logout, not merely token expiration."""
import asyncio
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, Request

from app.api.routes.auth import router as auth_router
from app.api.routes.trips import events
from app.auth import SESSION_COOKIE, lookup_user
from test_durable_trips import system
from test_local_auth import bootstrap, ORIGIN
from test_planner_graph import make_request


def test_open_sse_observes_logout(tmp_path):
    async def scenario():
        async with system(tmp_path) as runs:
            app = FastAPI()
            app.state.auth_sessions, app.state.run_manager = runs.sessions, runs
            app.include_router(auth_router, prefix='/api')
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url=ORIGIN) as client:
                headers = await bootstrap(client)
                registered = await client.post('/api/auth/register', headers=headers,
                    json={'email': f'{uuid4()}@example.test', 'password': 'stream-test-password'})
                assert registered.status_code == 201
                headers['X-CSRF-Token'] = registered.json()['csrf_token']
                owner = registered.json()['user']['id']
                created = await runs.create(owner, make_request(), str(uuid4()))
                await runs.tasks[created['id']]
                async def receive():
                    return {'type': 'http.request', 'body': b'', 'more_body': False}
                request = Request({'type': 'http', 'method': 'GET', 'path': '/', 'app': app,
                    'headers': [(b'cookie', f'{SESSION_COOKIE}={client.cookies.get(SESSION_COOKIE)}'.encode())]}, receive)
                user = await lookup_user(request)
                response = await events(UUID(created['id']), request, 0, user, runs)
                first = await anext(response.body_iterator)
                assert 'id:' in first
                assert (await client.post('/api/auth/logout', headers=headers)).status_code == 204
                remaining = ''.join([chunk async for chunk in response.body_iterator])
                assert 'event: session.expired' in remaining
                assert 'event: stream.closed' not in remaining
    asyncio.run(scenario())
