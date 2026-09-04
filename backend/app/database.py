"""Application records. Only the backend accesses these tables, never the browser."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now() -> datetime:
    return datetime.now(timezone.utc)


def uid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key"),
        Index("ix_trips_owner_created", "user_id", "created_at", "id"),
        Index("ix_trips_one_active", "user_id", unique=True,
              postgresql_where=text("status IN ('queued', 'running')"),
              sqlite_where=text("status IN ('queued', 'running')")),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(String(36))
    idempotency_key: Mapped[str] = mapped_column(String(36))
    title: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(24), default="queued")
    request: Mapped[dict] = mapped_column(JSON)
    plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    current_node: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str] = mapped_column(String(500), default="等待规划")
    run_id: Mapped[str] = mapped_column(String(36))
    resume_count: Mapped[int] = mapped_column(Integer, default=0)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    graph_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TripRun(Base):
    __tablename__ = "trip_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="queued")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TripEvent(Base):
    __tablename__ = "trip_events"
    __table_args__ = (Index("ix_trip_events_replay", "trip_id", "id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    run_id: Mapped[str] = mapped_column(String(36))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DailyUsage(Base):
    __tablename__ = "daily_usage"
    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    day: Mapped[str] = mapped_column(String(10), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


def create_database(url: str):
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    options: dict[str, Any] = {"pool_pre_ping": True, "echo": False, "hide_parameters": True}
    if url.startswith("postgresql"):
        options.update(pool_size=3, max_overflow=1, connect_args={"connect_timeout": 10})
    engine = create_async_engine(url, **options)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


def iso(value: datetime) -> str:
    return value.replace(tzinfo=value.tzinfo or timezone.utc).isoformat()


def serialize_trip(trip: Trip, *, detail: bool = True) -> dict:
    data = {"id": trip.id, "title": trip.title, "status": trip.status,
            "current_node": trip.current_node, "message": trip.message,
            "error_code": trip.error_code, "run_id": trip.run_id,
            "revision": trip.revision, "resume_count": trip.resume_count,
            "created_at": iso(trip.created_at), "updated_at": iso(trip.updated_at)}
    if detail:
        data.update(request=trip.request, plan=trip.plan, metadata=trip.model_metadata)
    return data
