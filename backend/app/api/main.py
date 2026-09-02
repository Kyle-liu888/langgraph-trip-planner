"""FastAPI application for the LangGraph trip planner."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import get_settings, print_config, validate_config
from .routes import map as map_routes
from .routes import poi, trip


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    print(f"\n🚀 {settings.app_name} v{settings.app_version}")
    print_config(settings)
    validate_config(settings)
    print(f"📚 API 文档: http://localhost:{settings.port}/docs")
    yield
    print("\n👋 LangGraph 旅行助手已关闭")


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
)
app.include_router(trip.router, prefix="/api")
app.include_router(poi.router, prefix="/api")
app.include_router(map_routes.router, prefix="/api")


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
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }
