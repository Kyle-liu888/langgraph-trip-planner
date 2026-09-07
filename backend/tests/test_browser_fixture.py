"""Tests for the disposable browser fixture; never touch user accounts or APIs."""
import asyncio
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import select

from app.database import Account
from browser_fixture import create_app, fixture_settings, merchant_fixture, plan_for_request
from test_planner_graph import make_request

ORIGIN = "http://127.0.0.1:18081"


def test_fixture_settings_ignore_environment_and_secrets(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://should-not-be-read")
    monkeypatch.setenv("LLM_API_KEY", "must-not-be-loaded")
    monkeypatch.setenv("AMAP_API_KEY", "must-not-be-loaded")
    monkeypatch.setenv("CORS_ORIGINS", "https://untrusted.example")
    settings = fixture_settings()
    assert settings.database_url is None
    assert settings.amap_api_key is None
    assert settings.llm_api_key is None
    assert settings.llm_base_url is None
    assert settings.llm_provider == "fake"
    assert settings.llm_model == "browser-fixture"
    assert settings.get_cors_origins_list() == [ORIGIN, "http://localhost:18081"]


def test_fixture_registration_sse_edit_logout_isolation_and_static_routes(tmp_path):
    index = tmp_path / "index.html"
    index.write_text('<html><body><div id="app">fixture bundle</div></body></html>', encoding="utf-8")

    async def scenario():
        app = create_app(tmp_path, model_delay=0)
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app)
            async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
                assert (await client.get("/health")).json()["is_test_fixture"] is True
                for route in ("/login", "/trips/new", "/trips/" + str(uuid4())):
                    page = await client.get(route)
                    assert page.status_code == 200 and "fixture bundle" in page.text
                    assert "隔离浏览器验收" in page.text
                    assert page.headers["X-Trip-Test-Fixture"] == "true"
                    assert "connect-src 'self'" in page.headers["Content-Security-Policy"]
                assert (await client.get("/api/unknown")).status_code == 404
                for route in ("/api/trips", "/api/poi/photo", "/api/poi/visit-info", "/api/poi/search",
                              "/api/poi/merchant-info?kind=hotel&city=北京&name=验收酒店"):
                    assert (await client.get(route)).status_code == 401

                bootstrap = await client.get("/api/auth/session")
                assert bootstrap.json()["user"] is None
                assert "trip_browser_fixture_csrf=" in bootstrap.headers["set-cookie"]
                headers = {"Origin": ORIGIN, "X-CSRF-Token": bootstrap.json()["csrf_token"]}
                credentials = {"email": "browser-test@example.test", "password": "temporary-test-password"}
                assert (await client.post("/api/auth/register", json=credentials)).status_code == 403
                bad = await client.post("/api/auth/register", json=credentials,
                                        headers={**headers, "Origin": "https://untrusted.example"})
                assert bad.status_code == 403
                registered = await client.post("/api/auth/register", json=credentials, headers=headers)
                assert registered.status_code == 201
                assert "trip_browser_fixture_session=" in registered.headers["set-cookie"]
                assert "trip_session=" not in registered.headers["set-cookie"]
                assert "trip_login_csrf=" not in registered.headers["set-cookie"]
                assert registered.json()["user"]["email_verified"] is False
                headers["X-CSRF-Token"] = registered.json()["csrf_token"]

                request = make_request().model_copy(update={"travel_days": 3, "end_date": "2026-10-03"})
                response = await client.post("/api/trips", json=request.model_dump(mode="json"),
                                            headers={**headers, "X-Idempotency-Key": str(uuid4())})
                assert response.status_code == 202
                trip_id = response.json()["id"]
                if task := app.state.run_manager.tasks.get(trip_id):
                    await task
                trip = (await client.get(f"/api/trips/{trip_id}")).json()
                assert trip["status"] == "completed", trip
                assert len(trip["plan"]["days"]) == 3
                assert trip["plan"]["end_date"] == "2026-10-03"
                assert trip["metadata"]["provider"] == "fake"
                stream = await client.get(f"/api/trips/{trip_id}/events")
                assert "event: run.completed" in stream.text
                assert "event: node.started" in stream.text and "event: stream.closed" in stream.text
                assert (await client.get("/api/trips")).json()["items"][0]["id"] == trip_id
                photo = (await client.get("/api/poi/photo")).json()["data"]
                assert photo["status"] == "no_photo" and photo["photo_url"] is None
                visit = (await client.get("/api/poi/visit-info", params={"visit_date": "2026-10-02"})).json()["data"]
                assert visit["visit_date"] == "2026-10-02" and visit["status"] == "unavailable"
                assert (await client.get("/api/poi/search")).json()["data"] == []
                merchant = (await client.get("/api/poi/merchant-info", params={
                    "kind": "hotel", "city": "北京", "name": "验收庭院酒店(王府井店)",
                })).json()["data"]
                assert merchant["match_status"] == "matched" and merchant["rating"] == "4.6"
                assert len(merchant["photos"]) == 3
                assert merchant["links"][0]["verified_at"] != merchant["queried_at"][:10]
                image = await client.get(merchant["photos"][0]["url"])
                assert image.status_code == 200 and image.headers["content-type"] == "image/svg+xml"
                assert "Fixture image" in image.text
                assert (await client.get("/fixture-assets/merchant-9.svg")).status_code == 404
                assert merchant["links"][0]["url"].endswith("/999999999999999999.html")
                assert trip["plan"]["days"][0]["hotel"]["rating"] == "9.9"
                assert trip["plan"]["days"][0]["meals"][1].get("location") is None

                plan = trip["plan"]
                plan["days"][0]["attractions"][0]["description"] = "验收编辑已保存"
                saved = await client.put(f"/api/trips/{trip_id}/plan",
                                         json={"plan": plan, "revision": trip["revision"]}, headers=headers)
                assert saved.status_code == 200 and saved.json()["revision"] == 2
                assert (await client.get(f"/api/trips/{trip_id}")).json()["plan"]["days"][0]["attractions"][0]["description"] == "验收编辑已保存"
                assert (await client.post("/api/auth/logout", headers=headers)).status_code == 204
                assert (await client.get(f"/api/trips/{trip_id}")).status_code == 401

                bootstrap = (await client.get("/api/auth/session")).json()
                headers["X-CSRF-Token"] = bootstrap["csrf_token"]
                login = await client.post("/api/auth/login", json=credentials, headers=headers)
                assert login.status_code == 200
                headers["X-CSRF-Token"] = login.json()["csrf_token"]
                assert (await client.get("/api/trips")).json()["items"][0]["id"] == trip_id
                async with app.state.auth_sessions() as session:
                    account = await session.scalar(select(Account))
                    assert account.password_hash.startswith("$argon2id$")

            # A second browser identity must not inherit the first account's history.
            async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as other:
                bootstrap = (await other.get("/api/auth/session")).json()
                registered = await other.post("/api/auth/register",
                    json={"email": "other-browser@example.test", "password": "another-test-password"},
                    headers={"Origin": ORIGIN, "X-CSRF-Token": bootstrap["csrf_token"]})
                assert registered.status_code == 201
                assert (await other.get("/api/trips")).json()["items"] == []
                assert (await other.get(f"/api/trips/{trip_id}")).status_code == 404

        # A fresh fixture process/lifespan starts with no persisted accounts/history.
        fresh = create_app(tmp_path, model_delay=0)
        async with fresh.router.lifespan_context(fresh):
            async with fresh.state.auth_sessions() as session:
                assert (await session.scalars(select(Account))).all() == []

    asyncio.run(scenario())


def test_merchant_fixture_covers_generic_missing_and_shared_hotel():
    import json

    request = make_request().model_copy(update={"travel_days": 3, "end_date": "2026-10-03"})
    plan = json.loads(plan_for_request(request))
    assert plan["days"][0]["hotel"] == plan["days"][2]["hotel"]
    for name, status in (("酒店自助早餐", "generic"), ("验收无资料餐馆(前门店)", "unmatched")):
        data = merchant_fixture("food", "北京", name, 18081)
        assert data["match_status"] == status and data["photos"] == []
        assert data["links"] == [] and data["source"] is None
    food = merchant_fixture("food", "北京", "验收烤鸭馆(王府井店)", 18081)
    assert food["food_tags"] == ["模拟烤鸭", "模拟家常菜"]
    for url in [photo["url"] for photo in food["photos"]]:
        assert url.startswith(ORIGIN + "/fixture-")
    assert food["links"][0]["url"] == "https://www.dianping.com/shop/fixturemerchant"
