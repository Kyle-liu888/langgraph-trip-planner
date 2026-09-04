import json
import logging
from fastapi.testclient import TestClient

from app.auth import csrf_for, digest
from app.observability import SafeFormatter, log_context


def test_session_and_csrf_hashes_are_domain_separated():
    assert len(digest('opaque-session')) == 64
    assert csrf_for('opaque-session') != digest('opaque-session')
    assert csrf_for('opaque-session') != csrf_for('another-session')


def test_log_redacts_secrets_and_does_not_dump_exception_input():
    context = log_context.set({'request_id': 'request-1', 'trip_id': 'trip-1'})
    try:
        try:
            raise ValueError('private prompt and customer details')
        except ValueError as exc:
            record = logging.LogRecord('test', logging.ERROR, __file__, 1,
                'failure Bearer abc.def.ghi sk-secretvalue', (), (type(exc), exc, exc.__traceback__))
        output = SafeFormatter(True).format(record)
        assert 'abc.def.ghi' not in output and 'sk-secretvalue' not in output
        assert 'private prompt' not in output
        payload = json.loads(output)
        assert payload['request_id'] == 'request-1' and payload['error_type'] == 'ValueError'
        assert payload['stack']
    finally:
        log_context.reset(context)


def test_main_auth_and_errors_never_echo_tokens():
    from app.api.main import app
    client = TestClient(app)  # no lifespan/cloud connection in this wiring test
    assert client.get('/api/trips').status_code == 401
    assert client.get('/api/poi/photo?name=test').status_code == 401
    assert client.post('/api/trip/plan', json={}).status_code == 410
    response = client.get('/api/trips/not-a-uuid', headers={'Authorization': 'Bearer invalid'})
    assert response.status_code in (401, 503)
    assert response.headers['x-request-id']
    assert 'Bearer invalid' not in response.text


def test_windows_uvicorn_loop_is_psycopg_compatible():
    import asyncio
    import uvicorn
    config = uvicorn.Config('app.api.main:app', loop='app.event_loop:selector_factory')
    loop = config.get_loop_factory()()
    try:
        assert isinstance(loop, asyncio.SelectorEventLoop)
    finally:
        loop.close()
