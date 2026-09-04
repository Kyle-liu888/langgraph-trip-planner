"""Offline auth integration; real database adapters, never real model/map requests."""
import asyncio
from datetime import timedelta
from uuid import uuid4

import httpx
from fastapi import Depends, FastAPI, Request
from sqlalchemy import select

from app.api.routes.auth import router
from app.auth import SESSION_COOKIE, digest, require_user, session_alive
from app.database import Account, Base, LoginSession, create_database, now

ORIGIN = "http://localhost:5173"


async def bootstrap(client):
    response = await client.get("/api/auth/session")
    assert response.status_code == 200
    return {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}


async def exercise_auth(sessions):
    app = FastAPI()
    app.state.auth_sessions = sessions
    app.include_router(router, prefix="/api")

    @app.post("/api/protected")
    async def protected(user=Depends(require_user)):
        return {"id": user.id}

    @app.get("/api/alive")
    async def alive(request: Request, user=Depends(require_user)):
        return {"alive": await session_alive(request, user)}

    transport = httpx.ASGITransport(app)
    async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
        email = f"{uuid4()}@example.test"
        credentials = {"email": email, "password": "test-password-1234"}
        assert (await client.post("/api/auth/register", json=credentials)).status_code == 403
        headers = await bootstrap(client)
        bad = {**headers, "Origin": "https://attacker.example"}
        assert (await client.post("/api/auth/register", json=credentials, headers=bad)).status_code == 403
        result = await client.post("/api/auth/register", json=credentials, headers=headers)
        assert result.status_code == 201
        assert "HttpOnly" in result.headers["set-cookie"] and "SameSite=strict" in result.headers["set-cookie"]
        assert "Max-Age=604800" in result.headers["set-cookie"]
        assert result.json()["user"]["email_verified"] is False
        user_id = result.json()["user"]["id"]
        token = client.cookies.get(SESSION_COOKIE)
        headers = {**headers, "X-CSRF-Token": result.json()["csrf_token"]}
        async with sessions() as db:
            account = await db.get(Account, user_id)
            assert account.password_hash.startswith("$argon2id$")
            assert credentials["password"] not in account.password_hash
            stored = await db.get(LoginSession, digest(token))
            assert stored and stored.token_hash != token
        assert (await client.post("/api/protected")).status_code == 403
        assert (await client.post("/api/protected", headers=headers)).json()["id"] == user_id
        assert (await client.get("/api/alive")).json()["alive"]
        stale_csrf = headers["X-CSRF-Token"]
        assert (await client.post("/api/auth/logout", headers=headers)).status_code == 204
        client.cookies.set(SESSION_COOKIE, token)
        assert (await client.get("/api/alive")).status_code == 401
        client.cookies.clear()
        headers = await bootstrap(client)
        wrong = await client.post("/api/auth/login", headers=headers,
                                  json={**credentials, "password": "wrong-password"})
        missing = await client.post("/api/auth/login", headers=headers,
                                    json={**credentials, "email": f"{uuid4()}@example.test"})
        assert wrong.status_code == missing.status_code == 401
        assert wrong.json() == missing.json()
        result = await client.post("/api/auth/login", headers=headers, json=credentials)
        assert result.status_code == 200 and result.json()["csrf_token"] != stale_csrf
        token = client.cookies.get(SESSION_COOKIE)
        async with sessions() as db:
            stored = await db.get(LoginSession, digest(token))
            stored.expires_at = now() - timedelta(seconds=1)
            await db.commit()
        assert (await client.get("/api/alive")).status_code == 401
        client.cookies.clear()
        headers = await bootstrap(client)
        for _ in range(11):
            limited = await client.post("/api/auth/login", headers=headers,
                                       json={**credentials, "password": "wrong-password"})
        assert limited.status_code == 429
    return user_id


def test_local_registration_csrf_hashes_logout_expiry_and_rate_limits(tmp_path):
    async def scenario():
        engine, sessions = create_database(f"sqlite+aiosqlite:///{tmp_path.as_posix()}/auth.db")
        try:
            async with engine.begin() as db:
                await db.run_sync(Base.metadata.create_all)
            await exercise_auth(sessions)
        finally:
            await engine.dispose()
    asyncio.run(scenario())
