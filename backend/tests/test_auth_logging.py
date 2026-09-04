import json
import logging
import time
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.auth import verify_token
from app.observability import SafeFormatter, log_context


def test_jwt_signature_owner_issuer_audience_and_expiration():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    user_id = str(uuid4())
    claims = {'sub': user_id, 'exp': int(time.time()) + 60, 'iss': 'https://example.supabase.co/auth/v1',
              'aud': 'authenticated', 'role': 'authenticated'}
    client = SimpleNamespace(get_signing_key_from_jwt=lambda token: SimpleNamespace(key=private.public_key()))
    with patch('app.auth.jwks_client', return_value=client):
        token = jwt.encode(claims, private, algorithm='RS256')
        assert verify_token(token, 'https://example.supabase.co', 'authenticated').id == user_id
        for invalid in ({'exp': 0}, {'iss': 'https://attacker.example/auth/v1'}, {'aud': 'other'},
                        {'role': 'anon'}, {'is_anonymous': True}, {'sub': 'not-a-uuid'}):
            bad = jwt.encode({**claims, **invalid}, private, algorithm='RS256')
            with pytest.raises((jwt.InvalidTokenError, ValueError)):
                verify_token(bad, 'https://example.supabase.co', 'authenticated')
        with pytest.raises(jwt.InvalidSignatureError):
            wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            verify_token(jwt.encode(claims, wrong_key, algorithm='RS256'), 'https://example.supabase.co', 'authenticated')


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
