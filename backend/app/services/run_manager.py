"""Single-process task ownership, durable events and checkpoint-based manual recovery."""
from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import delete, func, select, update

from ..database import DailyUsage, Trip, TripEvent, TripRun, now, serialize_trip
from ..models.schemas import TripPlan, TripRequest
from ..observability import log_context, logger, redact


ACTIVE = {"queued", "running"}
TERMINAL = {"completed", "fallback", "failed", "interrupted"}


def problem(status: int, code: str, message: str):
    return HTTPException(status, {"code": code, "message": message})


class RunManager:
    def __init__(self, sessions, planner, checkpointer, settings):
        self.sessions, self.planner = sessions, planner
        self.checkpointer, self.settings = checkpointer, settings
        self.tasks: dict[str, asyncio.Task] = {}
        self.changed: dict[str, asyncio.Event] = {}
        self.mutations = asyncio.Lock()
        self.slots = asyncio.Semaphore(settings.max_concurrent_runs)
        self.closing = False

    async def owned(self, session, trip_id: str, user_id: str) -> Trip:
        trip = await session.scalar(select(Trip).where(Trip.id == trip_id, Trip.user_id == user_id))
        if trip is None:
            raise problem(404, "TRIP_NOT_FOUND", "行程不存在或无权访问")
        return trip

    async def recover_interrupted(self):
        async with self.sessions() as session:
            pending = (await session.scalars(select(Trip).where(Trip.status.in_(ACTIVE)))).all()
        for trip in pending:
            await self.finish(trip.id, trip.run_id, "interrupted", "服务已重启，请点击继续规划", "PROCESS_RESTARTED")

    async def add_event(self, trip_id: str, run_id: str, payload: dict, *, session=None):
        safe = json.loads(redact(json.dumps(payload, ensure_ascii=False, default=str)))
        safe.update(trip_id=trip_id, run_id=run_id)
        event = TripEvent(trip_id=trip_id, run_id=run_id, payload=safe)
        if session is not None:
            session.add(event)
            return
        async with self.sessions() as db:
            db.add(event)
            if payload.get("type") == "node.started":
                await db.execute(update(Trip).where(Trip.id == trip_id, Trip.run_id == run_id).values(
                    current_node=payload.get("node"), updated_at=now()))
            await db.commit()
        if signal := self.changed.get(trip_id):
            signal.set()

    def spawn(self, trip_id: str, run_id: str, user_id: str, resume: bool):
        self.changed.setdefault(trip_id, asyncio.Event())
        task = asyncio.create_task(self.execute(trip_id, run_id, user_id, resume), name=f"trip:{trip_id}")
        self.tasks[trip_id] = task

        def done(finished):
            if self.tasks.get(trip_id) is finished:
                self.tasks.pop(trip_id, None)
                self.changed.pop(trip_id, None)
            if not finished.cancelled() and finished.exception():
                logger.error("run.task_crashed", extra={"trip_id": trip_id,
                             "error_type": type(finished.exception()).__name__})
        task.add_done_callback(done)

    async def create(self, user_id: str, request: TripRequest, key: str) -> dict:
        async with self.mutations, self.sessions() as session:
            existing = await session.scalar(select(Trip).where(Trip.user_id == user_id, Trip.idempotency_key == key))
            body = request.model_dump(mode="json")
            if existing:
                if existing.request != body:
                    raise problem(409, "IDEMPOTENCY_CONFLICT", "此请求标识已用于其他行程")
                return serialize_trip(existing)
            if self.closing:
                raise problem(503, "SHUTTING_DOWN", "服务正在关闭，请稍后重试")
            await self.check_active(session, user_id)
            # Quota is kept separately so deleting a trip cannot refund its cost.
            day = (now() + timedelta(hours=8)).date().isoformat()
            usage = await session.get(DailyUsage, (user_id, day))
            if usage and usage.count >= self.settings.daily_trip_limit:
                raise problem(429, "DAILY_LIMIT", "今日规划次数已用完，明天再来；失败行程仍可继续")
            if usage is None:
                usage = DailyUsage(user_id=user_id, day=day, count=0)
                session.add(usage)
            usage.count += 1
            trip_id, run_id = str(uuid4()), str(uuid4())
            trip = Trip(id=trip_id, user_id=user_id, idempotency_key=key,
                        title=f"{request.city} · {request.travel_days}天 · {request.start_date}",
                        request=body, run_id=run_id)
            session.add(trip)
            await session.flush()
            session.add(TripRun(id=run_id, trip_id=trip_id))
            await self.add_event(trip_id, run_id, {"type": "run.queued", "label": "等待规划"}, session=session)
            await session.commit()
            result = serialize_trip(trip)
            self.spawn(trip_id, run_id, user_id, False)
            return result

    async def check_active(self, session, user_id):
        active = await session.scalar(select(Trip.id).where(Trip.user_id == user_id, Trip.status.in_(ACTIVE)).limit(1))
        if active:
            raise problem(409, "ACTIVE_TRIP", "已有行程正在规划，请先等待它完成")

    async def resume(self, trip_id: str, user_id: str):
        async with self.mutations, self.sessions() as session:
            trip = await self.owned(session, trip_id, user_id)
            if trip.status not in {"failed", "interrupted"}:
                raise problem(409, "NOT_RESUMABLE", "只有失败或中断的行程可以继续")
            if trip.resume_count >= self.settings.max_resume_attempts:
                raise problem(429, "RESUME_LIMIT", "此行程已达到恢复次数上限，请检查配置后新建行程")
            if trip.graph_version != 1:
                raise problem(409, "GRAPH_VERSION", "此行程检查点版本不兼容，请新建行程")
            if self.closing:
                raise problem(503, "SHUTTING_DOWN", "服务正在关闭")
            await self.check_active(session, user_id)
            trip.resume_count += 1
            trip.run_id = str(uuid4())
            trip.status, trip.message, trip.error_code = "queued", "等待继续规划", None
            trip.updated_at = now()
            session.add(TripRun(id=trip.run_id, trip_id=trip.id))
            await self.add_event(trip.id, trip.run_id, {"type": "run.queued", "label": "等待继续规划"}, session=session)
            await session.commit()
            self.spawn(trip.id, trip.run_id, user_id, True)
            return serialize_trip(trip)

    async def execute(self, trip_id: str, run_id: str, user_id: str, resume: bool):
        token = log_context.set({**log_context.get(), "trip_id": trip_id, "run_id": run_id, "user_id": user_id})
        try:
            async with self.slots:
                async with self.sessions() as session:
                    trip = await self.owned(session, trip_id, user_id)
                    trip.status, trip.message = "running", "正在规划"
                    await session.execute(update(TripRun).where(TripRun.id == run_id).values(status="running"))
                    await session.commit()
                    request = trip.request
                await self.add_event(trip_id, run_id, {"type": "run.started", "label": "继续规划" if resume else "开始规划"})
                config = {"configurable": {"thread_id": trip_id}}
                snapshot = await self.planner.graph.aget_state(config)
                inputs = None if resume and snapshot.values else {"request": request}
                async with asyncio.timeout(self.settings.planner_request_timeout):
                    # If the graph completed just before a crash, persist its result without re-running it.
                    if not (resume and snapshot.values.get("trip_plan") and not snapshot.next):
                        async for part in self.planner.graph.astream(inputs, config=config,
                                context=self.planner.runtime, stream_mode="custom", version="v2"):
                            if part["type"] == "custom":
                                await self.add_event(trip_id, run_id, part["data"])
                    snapshot = await self.planner.graph.aget_state(config)
                    result = snapshot.values
                    plan = TripPlan.model_validate(result["trip_plan"]).model_dump(mode="json")
                status = "fallback" if result.get("generation_status") == "fallback_success" else "completed"
                await self.finish(trip_id, run_id, status, result.get("generation_message", "规划完成"),
                                  plan=plan, metadata=result.get("model_metadata", {}))
        except asyncio.CancelledError:
            await self.finish(trip_id, run_id, "interrupted", "服务已停止，可从检查点继续", "PROCESS_STOPPED")
            raise
        except Exception as exc:
            logger.exception("run.failed", extra={"error_type": type(exc).__name__})
            code = "RUN_TIMEOUT" if isinstance(exc, TimeoutError) else "RUN_FAILED"
            message = "规划超时，可稍后继续" if isinstance(exc, TimeoutError) else "规划失败，请查看运行日志或稍后继续"
            await self.finish(trip_id, run_id, "failed", message, code)
        finally:
            log_context.reset(token)

    async def finish(self, trip_id, run_id, status, message, code=None, *, plan=None, metadata=None):
        async with self.sessions() as session:
            trip = await session.get(Trip, trip_id)
            if not trip or trip.run_id != run_id:
                return
            trip.status, trip.message, trip.error_code = status, message[:500], code
            trip.updated_at = now()
            if plan is not None:
                trip.plan, trip.model_metadata = plan, metadata or {}
            await session.execute(update(TripRun).where(TripRun.id == run_id).values(status=status, finished_at=now()))
            kind = "run.completed" if status in {"completed", "fallback"} else f"run.{status}"
            await self.add_event(trip_id, run_id, {"type": kind, "status": status, "label": trip.message,
                                                 "error_code": code}, session=session)
            await session.commit()
        if signal := self.changed.get(trip_id):
            signal.set()
        logger.info("run.finished", extra={"trip_id": trip_id, "run_id": run_id, "status": status})

    async def remove(self, trip_id, user_id):
        async with self.mutations, self.sessions() as session:
            trip = await self.owned(session, trip_id, user_id)
            if trip.status in ACTIVE:
                raise problem(409, "TRIP_RUNNING", "请等待规划结束后再删除")
            await self.checkpointer.adelete_thread(trip_id)
            await session.execute(delete(TripEvent).where(TripEvent.trip_id == trip_id))
            await session.execute(delete(TripRun).where(TripRun.trip_id == trip_id))
            await session.delete(trip)
            await session.commit()

    async def close(self):
        self.closing = True
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
