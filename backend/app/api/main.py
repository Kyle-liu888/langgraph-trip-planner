"""FastAPI application for the LangGraph trip planner."""

from contextlib import asynccontextmanager, AsyncExitStack
from time import perf_counter
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from sqlalchemy import text

from ..auth import require_user
from ..config import get_settings
from ..database import create_database
from ..observability import configure_logging, log_context, logger
from ..services.run_manager import RunManager
from ..services.trip_planner_service import TripPlannerService
from .routes import map as map_routes
from .routes import poi, trips


settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI):
    configure_logging(settings)
    application.state.run_manager = None
    engine = None
    async with AsyncExitStack() as stack:
        stage = "configuration"
        try:
            url = settings.secret_value("database_url")
            if url:
                stage = "business_database_and_migrations"
                engine, sessions = create_database(url)
                async with engine.connect() as db:
                    await db.execute(text("SELECT id FROM trips LIMIT 0"))
                connection = await stack.enter_async_context(await AsyncConnection.connect(
                    url, autocommit=True, prepare_threshold=0, row_factory=dict_row,
                    connect_timeout=10))
                # SET works with session poolers without requiring startup-option forwarding.
                await connection.execute("SET search_path TO planner_internal")
                cursor = await connection.execute("SELECT pg_try_advisory_lock(732981204) AS acquired")
                if not (await cursor.fetchone())["acquired"]:
                    raise RuntimeError("Another planner process owns the database")
                stage = "checkpoint_tables"
                saver = AsyncPostgresSaver(connection)
                await saver.setup()
                stage = "model_configuration"
                planner = TripPlannerService(settings=settings, checkpointer=saver)
                runs = RunManager(sessions, planner, saver, settings)
                await runs.recover_interrupted()
                application.state.run_manager = runs
                logger.info("storage.ready")
            else:
                logger.warning("storage.not_configured", extra={"hint": "Configure DATABASE_URL and run alembic upgrade head"})
        except Exception:
            logger.exception("storage.startup_failed", extra={"stage": stage})
        logger.info("server.started", extra={"port": settings.port, "logs": str(settings.log_dir)})
        try:
            yield
        finally:
            if application.state.run_manager:
                await application.state.run_manager.close()
            if engine:
                await engine.dispose()
            logger.info("server.stopped")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于 LangChain、LangGraph 与高德地图数据的模型无关旅行规划 API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.include_router(trips.router, prefix="/api")
app.include_router(poi.router, prefix="/api", dependencies=[Depends(require_user)])
app.include_router(map_routes.router, prefix="/api", dependencies=[Depends(require_user)])


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    token = log_context.set({"request_id": request_id})
    started = perf_counter()
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info("http.response", extra={"method": request.method, "path": request.url.path,
                    "status": response.status_code, "elapsed_ms": round((perf_counter() - started) * 1000)})
        return response
    finally:
        log_context.reset(token)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "REQUEST_FAILED", "message": "请求失败，请检查参数或服务日志"}
    return JSONResponse({"detail": detail, "request_id": getattr(request.state, "request_id", None)},
                        status_code=exc.status_code, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse({"detail": {"code": "INVALID_REQUEST", "message": "请求参数不符合要求",
                         "fields": [".".join(map(str, item["loc"])) for item in exc.errors()]},
                         "request_id": getattr(request.state, "request_id", None)}, status_code=422)


@app.exception_handler(Exception)
async def server_error(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.error("http.failed", exc_info=(type(exc), exc, exc.__traceback__), extra={"request_id": request_id})
    return JSONResponse({"detail": {"code": "INTERNAL_ERROR", "message": "服务异常，请凭请求编号查询日志"},
                         "request_id": request_id}, status_code=500)


@app.post("/api/trip/plan", status_code=410)
async def legacy_plan():
    raise HTTPException(410, {"code": "API_REPLACED", "message": "请登录后使用 POST /api/trips 和 SSE 进度接口"})


@app.get("/")
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "framework": "LangGraph",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> dict:
    ready = getattr(app.state, "run_manager", None) is not None
    return {
        "status": "healthy" if ready else "degraded",
        "storage_ready": ready,
        "auth_configured": bool(settings.supabase_url),
        "service": settings.app_name,
        "version": settings.app_version,
    }
