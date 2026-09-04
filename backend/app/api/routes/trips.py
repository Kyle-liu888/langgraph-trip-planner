"""Authenticated, durable trip resources and resumable progress subscriptions."""
import asyncio
import json
import time
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select

from ...auth import User, require_user, session_alive
from ...database import DailyUsage, Trip, TripEvent, iso, now, serialize_trip
from ...models.schemas import TripPlan, TripRequest
from ...services.run_manager import ACTIVE, RunManager, problem


router = APIRouter(tags=["行程与进度"])


def manager(request: Request) -> RunManager:
    value = getattr(request.app.state, "run_manager", None)
    if value is None:
        raise problem(503, "STORAGE_NOT_READY", "本地数据库尚未就绪，请配置 DATABASE_URL 并执行数据库迁移")
    return value


@router.post("/trips", status_code=202)
async def create_trip(body: TripRequest, idempotency_key: UUID = Header(alias="X-Idempotency-Key"),
                      user: User = Depends(require_user), runs: RunManager = Depends(manager)):
    return await runs.create(user.id, body, str(idempotency_key))


@router.get("/trips")
async def list_trips(cursor: UUID | None = None, limit: int = Query(20, ge=1, le=50),
                     user: User = Depends(require_user), runs: RunManager = Depends(manager)):
    async with runs.sessions() as session:
        query = select(Trip).where(Trip.user_id == user.id)
        if cursor:
            anchor = await runs.owned(session, str(cursor), user.id)
            query = query.where(or_(Trip.created_at < anchor.created_at,
                                    and_(Trip.created_at == anchor.created_at, Trip.id < anchor.id)))
        items = (await session.scalars(query.order_by(Trip.created_at.desc(), Trip.id.desc()).limit(limit + 1))).all()
        return {"items": [serialize_trip(item, detail=False) for item in items[:limit]],
                "next_cursor": items[limit - 1].id if len(items) > limit else None}


@router.get("/trips/{trip_id}")
async def get_trip(trip_id: UUID, user: User = Depends(require_user), runs: RunManager = Depends(manager)):
    async with runs.sessions() as session:
        return serialize_trip(await runs.owned(session, str(trip_id), user.id))


class RenameTrip(BaseModel):
    title: str = Field(min_length=1, max_length=160)


@router.patch("/trips/{trip_id}")
async def rename_trip(trip_id: UUID, body: RenameTrip, user: User = Depends(require_user), runs: RunManager = Depends(manager)):
    title = body.title.strip()
    if not title:
        raise problem(422, "EMPTY_TITLE", "标题不能为空")
    async with runs.mutations, runs.sessions() as session:
        trip = await runs.owned(session, str(trip_id), user.id)
        trip.title, trip.updated_at = title, now()
        await session.commit()
        return serialize_trip(trip)


class SavePlan(BaseModel):
    plan: TripPlan
    revision: int = Field(ge=1)


@router.put("/trips/{trip_id}/plan")
async def save_plan(trip_id: UUID, body: SavePlan, user: User = Depends(require_user), runs: RunManager = Depends(manager)):
    async with runs.mutations, runs.sessions() as session:
        trip = await runs.owned(session, str(trip_id), user.id)
        if trip.status not in {"completed", "fallback"}:
            raise problem(409, "PLAN_NOT_READY", "行程尚未完成，暂不能修改")
        if trip.revision != body.revision:
            raise problem(409, "REVISION_CONFLICT", "行程已在其他页面更新，请刷新后再编辑")
        if body.plan.city != trip.request["city"]:
            raise problem(422, "CITY_MISMATCH", "编辑行程不能改变目的地")
        trip.plan, trip.updated_at = body.plan.model_dump(mode="json"), now()
        trip.revision += 1
        await session.commit()
        return serialize_trip(trip)


@router.delete("/trips/{trip_id}", status_code=204)
async def delete_trip(trip_id: UUID, user: User = Depends(require_user), runs: RunManager = Depends(manager)):
    await runs.remove(str(trip_id), user.id)
    return Response(status_code=204)


@router.post("/trips/{trip_id}/resume", status_code=202)
async def resume_trip(trip_id: UUID, user: User = Depends(require_user), runs: RunManager = Depends(manager)):
    return await runs.resume(str(trip_id), user.id)


@router.get("/me/usage")
async def usage(user: User = Depends(require_user), runs: RunManager = Depends(manager)):
    from datetime import timedelta
    day = (now() + timedelta(hours=8)).date().isoformat()
    async with runs.sessions() as session:
        value = await session.get(DailyUsage, (user.id, day))
        active = await session.scalar(select(Trip.id).where(Trip.user_id == user.id, Trip.status.in_(ACTIVE)))
        return {"day": day, "timezone": "Asia/Shanghai", "used": value.count if value else 0,
                "limit": runs.settings.daily_trip_limit, "active_trip_id": active,
                "max_resume_attempts": runs.settings.max_resume_attempts}


@router.get("/trips/{trip_id}/events")
async def events(trip_id: UUID, request: Request, last_event_id: int = Header(0, alias="Last-Event-ID", ge=0),
                 user: User = Depends(require_user), runs: RunManager = Depends(manager)):
    trip_key = str(trip_id)
    async with runs.sessions() as session:
        await runs.owned(session, trip_key, user.id)

    async def stream():
        cursor = last_event_id
        while not await request.is_disconnected():
            if not await session_alive(request, user):
                yield 'event: session.expired\ndata: {}\n\n'
                return
            # Clear before querying: a concurrent commit cannot be missed while waiting.
            signal = runs.changed.get(trip_key)
            if signal:
                signal.clear()
            async with runs.sessions() as session:
                trip = await session.scalar(select(Trip).where(Trip.id == trip_key, Trip.user_id == user.id))
                if trip is None:
                    yield 'event: trip.deleted\ndata: {}\n\n'
                    return
                rows = (await session.scalars(select(TripEvent).where(TripEvent.trip_id == trip_key,
                              TripEvent.id > cursor).order_by(TripEvent.id).limit(100))).all()
                status = trip.status
            for row in rows:
                cursor = row.id
                payload = {**row.payload, "sequence": row.id, "timestamp": iso(row.created_at)}
                yield f"id: {row.id}\nevent: {payload['type']}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            if rows:
                continue
            if status not in ACTIVE:
                yield 'event: stream.closed\ndata: {}\n\n'
                return
            try:
                if signal:
                    await asyncio.wait_for(signal.wait(), runs.settings.sse_heartbeat_seconds)
                else:
                    await asyncio.sleep(min(1, runs.settings.sse_heartbeat_seconds))
            except TimeoutError:
                yield ': heartbeat\n\n'

    return StreamingResponse(stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})
