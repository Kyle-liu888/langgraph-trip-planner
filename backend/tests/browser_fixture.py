"""Isolated browser acceptance server: real auth/trips, fake model/maps, disposable data.

Run from backend with the locked development dependencies installed:
    uv run --locked python tests/browser_fixture.py --help

Build frontend with VITE_API_BASE_URL='', VITE_AMAP_WEB_JS_KEY='' and
VITE_AMAP_WEB_KEY='' into a separate directory, then pass --dist. Never mount
personal .env/config files into the test container. No anonymous auth bypass or
pre-created account is provided; register through the real login page.

Bind 127.0.0.1 by default. --host 0.0.0.0 is only for an isolated container whose
published port is explicitly bound to 127.0.0.1 on the host. This is NOT a
deployment entry point. All accounts, sessions, trips and checkpoints disappear
when this process stops. No production PostgreSQL or external APIs are used.
"""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import ExitStack, asynccontextmanager
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

# Support direct execution without requiring installation as a Python package.
BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.checkpoint.memory import MemorySaver

from app.api.routes.auth import router as auth_router
from app.api.routes.trips import router as trips_router
from app.auth import require_user
from app.config import Settings
from app.database import Base, create_database
from app.graph import PlannerRuntime, build_planner_graph
from app.llm.config import ModelConfig
from app.models.schemas import TripRequest
from app.services.run_manager import RunManager
from test_planner_graph import StubContextBuilder, valid_plan_json


class FixtureSettings(Settings):
    """Use only explicit constructor values, never env/.env/secrets sources."""

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings,
                                   dotenv_settings, file_secret_settings):
        return (init_settings,)


def fixture_settings(port: int = 18081) -> FixtureSettings:
    return FixtureSettings(
        _env_file=None,
        llm_provider="fake",
        LLM_MODEL="browser-fixture",
        cors_origins=f"http://127.0.0.1:{port},http://localhost:{port}",
        planner_max_attempts=1,
        planner_enable_rerank=False,
        max_concurrent_runs=1,  # Keep the request-aware fake model serialized.
        daily_trip_limit=20,
        log_file_enabled=False,
        session_cookie_secure=False,
    )


def plan_for_request(request: TripRequest) -> str:
    """Adapt the existing offline graph fixture to the submitted trip dates."""
    plan = json.loads(valid_plan_json())
    original_day = plan["days"][0]
    original_weather = plan["weather_info"][0]
    plan.update(city=request.city, start_date=request.start_date, end_date=request.end_date)
    plan["days"], plan["weather_info"] = [], []
    stops = [
        ("故宫博物院", "B000A8UIN8", 116.397, 39.916),
        ("天坛公园", "B000A81CB2", 116.410, 39.881),
        ("颐和园", "B000A7O1CU", 116.273, 39.999),
    ]
    for index in range(request.travel_days):
        day = deepcopy(original_day)
        day_date = (date.fromisoformat(request.start_date) + timedelta(days=index)).isoformat()
        name, poi_id, longitude, latitude = stops[index % len(stops)]
        day.update(date=day_date, day_index=index, transportation=request.transportation,
                   accommodation=request.accommodation, description="浏览器验收模拟行程")
        day["attractions"][0].update(
            name=name, poi_id=poi_id, description="模拟景点，用于验证页面交互，不代表真实推荐。",
            location={"longitude": longitude, "latitude": latitude},
        )
        day["hotel"] = {
            "name": "验收庭院酒店(王府井店)", "address": "北京市东城区模拟胡同8号",
            "location": {"longitude": 116.4101, "latitude": 39.9131},
            "price_range": "300-400元", "rating": "9.9", "distance": "模拟位置",
            "type": "经济型酒店", "estimated_cost": 350,
        }
        day["meals"] = [
            {"type": "breakfast", "name": "酒店自助早餐", "estimated_cost": 0,
             "description": "是否包含早餐请向酒店确认。"},
            {"type": "lunch", "name": "验收烤鸭馆(王府井店)",
             "address": "北京市东城区模拟街16号", "estimated_cost": 80,
             "description": "行程中的用餐建议，不是平台评论。"},
            {"type": "dinner", "name": "验收无资料餐馆(前门店)",
             "address": "北京市东城区模拟街28号", "estimated_cost": 100,
             "description": "用于检查资料缺失时的页面降级。"},
        ]
        plan["days"].append(day)
        plan["weather_info"].append({**original_weather, "date": day_date,
                                     "day_weather": "测试天气", "night_weather": "测试天气"})
    plan["overall_suggestions"] = "这是隔离验收数据；模型、地图、天气均未调用真实服务。"
    plan["budget"] = {key: value * request.travel_days for key, value in plan["budget"].items()}
    return json.dumps(plan, ensure_ascii=False)


def merchant_fixture(kind: str, city: str, name: str, port: int) -> dict:
    """Deliberately synthetic sources: never claim these are real merchant links."""
    queried_at = "2026-09-07T08:00:00+00:00"
    result = {
        "match_status": "unmatched", "data_status": "no_data",
        "message": "隔离验收：暂无可核验门店资料", "place": None,
        "photos": [], "rating": None, "food_tags": [], "source": None,
        "links": [], "queried_at": queried_at,
    }
    if name in {"酒店早餐", "酒店自助早餐", "当地小吃"}:
        return {**result, "match_status": "generic", "message": "通用用餐安排，不对应具体门店"}
    if name not in {"验收庭院酒店(王府井店)", "验收烤鸭馆(王府井店)"}:
        return result
    hotel = kind == "hotel"
    address = "北京市东城区模拟胡同8号" if hotel else "北京市东城区模拟街16号"
    return {**result,
        "match_status": "matched", "data_status": "available",
        "message": "隔离验收：仅用于页面测试的模拟资料",
        "place": {"poi_id": "FIXTURE_HOTEL" if hotel else "FIXTURE_FOOD", "name": name,
                  "address": address, "city": city,
                  "location": {"longitude": 116.4101 if hotel else 116.4151, "latitude": 39.9131}},
        "photos": [{"url": f"http://127.0.0.1:{port}/fixture-assets/merchant-{index}.svg",
                    "title": f"模拟照片 {index}"} for index in range(1, 4)],
        "rating": "4.6" if hotel else "4.7", "food_tags": [] if hotel else ["模拟烤鸭", "模拟家常菜"],
        "source": {"name": "高德地图（隔离模拟）", "url": f"https://uri.amap.com/marker?poiid=FIXTURE_{'HOTEL' if hotel else 'FOOD'}",
                   "queried_at": queried_at},
        "links": [{"platform": "ctrip" if hotel else "dianping", "label": "携程" if hotel else "大众点评",
                   "url": "https://hotels.ctrip.com/hotels/999999999999999999.html" if hotel
                       else "https://www.dianping.com/shop/fixturemerchant",
                   "verified_at": "2026-09-01"}],
    }


class FixtureContextBuilder(StubContextBuilder):
    def __init__(self, model):
        self.model = model

    def collect(self, request):
        self.model.responses = [plan_for_request(request)]
        self.model.i = 0
        return super().collect(request)


def create_app(dist: Path | None = None, *, port: int = 18081, model_delay: float = 2) -> FastAPI:
    settings = fixture_settings(port)
    static_root = (dist or BACKEND.parent / "frontend" / "dist").resolve()

    @asynccontextmanager
    async def lifespan(app):
        with TemporaryDirectory(prefix="trip-browser-fixture-") as temporary, ExitStack() as patches:
            # The production helpers call these directly rather than through Depends.
            # Patch only for this isolated app lifespan and restore them on exit.
            patches.enter_context(patch("app.auth.get_settings", return_value=settings))
            patches.enter_context(patch("app.api.routes.auth.get_settings", return_value=settings))
            # Cookies share a host across ports: never overwrite the user's 5173 session.
            for module in ("app.auth", "app.api.routes.auth"):
                patches.enter_context(patch(f"{module}.SESSION_COOKIE", "trip_browser_fixture_session"))
                patches.enter_context(patch(f"{module}.CSRF_COOKIE", "trip_browser_fixture_csrf"))
            engine, sessions = create_database(f"sqlite+aiosqlite:///{temporary}/fixture.db")
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            saver = MemorySaver()
            model = FakeListChatModel(responses=[valid_plan_json()], sleep=model_delay)
            runtime = PlannerRuntime(
                model=model,
                model_config=ModelConfig(provider="fake", model="browser-fixture",
                    structured_output_mode="prompt", streaming=False, progress_interval=1),
                context_builder=FixtureContextBuilder(model), settings=settings,
            )
            runs = RunManager(sessions, SimpleNamespace(
                graph=build_planner_graph(saver), runtime=runtime), saver, settings)
            app.state.auth_sessions = sessions
            app.state.run_manager = runs
            app.state.fixture_settings = settings
            try:
                yield
            finally:
                await runs.close()
                await engine.dispose()

    app = FastAPI(title="旅行助手 · 隔离浏览器验收", lifespan=lifespan)
    app.include_router(auth_router, prefix="/api")
    app.include_router(trips_router, prefix="/api")

    @app.middleware("http")
    async def test_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Trip-Test-Fixture"] = "true"
        response.headers["Cache-Control"] = "no-store"
        # Browser acceptance cannot accidentally load paid map SDKs or remote imagery.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; connect-src 'self'; "
            "img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
            "font-src 'self' data:; object-src 'none'; base-uri 'self'"
        )
        return response

    @app.get("/health")
    async def health():
        return {"status": "ok", "is_test_fixture": True, "external_apis": "disabled",
                "database": "temporary SQLite", "checkpointer": "memory"}

    @app.get("/api/poi/photo")
    async def photo(user=Depends(require_user)):
        return {"success": True, "data": {"photo_url": None, "source": None, "status": "no_photo"}}

    @app.get("/api/poi/search")
    async def search(user=Depends(require_user)):
        return {"success": True, "data": [], "message": "隔离验收：地图查询已模拟"}

    @app.get("/api/poi/visit-info")
    async def visit_info(visit_date: str | None = None, user=Depends(require_user)):
        return {"success": True, "data": {
            "status": "unavailable", "match_status": "unknown", "poi_id": None,
            "visit_date": visit_date,
            "opening": {"today": None, "today_date": None, "regular": None, "scope": "reference_only"},
            "source_name": "隔离验收模拟数据", "source_url": None,
            "fetched_at": "", "upstream_updated_at": None, "official": None,
            "notice": "隔离验收：未查询真实开放时间；攻略入口仍可正常检查。",
        }}

    @app.get("/api/poi/merchant-info")
    async def merchant_info(kind: str, city: str, name: str, user=Depends(require_user)):
        return {"success": True, "data": merchant_fixture(kind, city, name, port)}

    @app.get("/fixture-assets/merchant-{index}.svg")
    async def merchant_image(index: int):
        if index not in (1, 2, 3):
            raise HTTPException(404)
        # Local placeholder artwork is test data, not generated or fetched merchant imagery.
        colors = {1: "#dfd2ba", 2: "#c2d3c8", 3: "#d6c6bd"}
        return Response(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="320">'
            f'<rect width="480" height="320" fill="{colors[index]}"/>'
            f'<text x="40" y="165" font-size="32" fill="#324c43">Fixture image {index}</text></svg>',
            media_type="image/svg+xml",
        )

    @app.get("/{path:path}", include_in_schema=False)
    async def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Unknown fixture API")
        candidate = (static_root / path).resolve()
        if not candidate.is_relative_to(static_root):
            raise HTTPException(404)
        if candidate.is_file() and candidate.name != "index.html":
            return FileResponse(candidate)
        index = static_root / "index.html"
        if not index.is_file():
            raise HTTPException(503, "Build frontend with empty API/map keys and pass --dist.")
        banner = (
            '<div role="status" style="padding:8px 16px;background:#fff4d6;color:#5b4210;'
            'font:14px sans-serif;text-align:center">'
            '隔离浏览器验收 · 模型与地图均为模拟数据 · 重启后数据清空</div>'
        )
        return HTMLResponse(index.read_text(encoding="utf-8").replace("<body>", "<body>" + banner, 1))

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", choices=["127.0.0.1", "0.0.0.0"], default="127.0.0.1",
                        help="0.0.0.0 only inside an isolated container with loopback port publishing")
    parser.add_argument("--port", type=int, default=18081)
    parser.add_argument("--dist", type=Path, default=BACKEND.parent / "frontend" / "dist")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if not (args.dist / "index.html").is_file():
        parser.error("--dist must contain a separately built frontend index.html")
    import uvicorn
    uvicorn.run(create_app(args.dist, port=args.port), host=args.host, port=args.port, access_log=True)


if __name__ == "__main__":
    main()
