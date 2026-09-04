"""Safe operational logs and LangGraph progress events (never prompt traces)."""

from __future__ import annotations

import contextvars
import functools
import inspect
import json
import logging
import re
import time
import traceback
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from langgraph.config import get_stream_writer


log_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar("log_context", default={})
logger = logging.getLogger("trip_planner")
NODE_LABELS = {
    "collect_context": "获取景点、餐饮和天气信息",
    "build_prompt": "整理规划条件",
    "generate_candidate": "模型生成候选行程",
    "validate_candidate": "校验候选行程",
    "select_best_candidate": "选择最佳行程",
    "create_fallback": "生成兜底行程",
}
_secrets: tuple[str, ...] = ()
_standard_fields = frozenset(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


def redact(value: str) -> str:
    for secret in _secrets:
        value = value.replace(secret, "[REDACTED]")
    value = re.sub(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", value)
    return re.sub(r"\bsk-[A-Za-z0-9_-]+", "[REDACTED]", value)


class SafeFormatter(logging.Formatter):
    def __init__(self, json_output: bool = False) -> None:
        super().__init__()
        self.json_output = json_output

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            **log_context.get(),
        }
        payload.update({key: value for key, value in record.__dict__.items() if key not in _standard_fields})
        if record.exc_info and record.exc_info[0]:
            # Exception messages (especially Pydantic errors) may embed complete input.
            # Keep the exception type and stack location, not its message or locals.
            payload["error_type"] = record.exc_info[0].__name__
            payload["stack"] = [f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}"
                                for frame in traceback.extract_tb(record.exc_info[2])]
        encoded = redact(json.dumps(payload, ensure_ascii=False, default=str))
        if self.json_output:
            return encoded
        safe = json.loads(encoded)
        fields = " ".join(f"{key}={value}" for key, value in safe.items()
                          if key not in {"timestamp", "level", "logger", "event"})
        return f"{safe['timestamp']} {safe['level']:<7} {safe['event']} {fields}".rstrip()


def configure_logging(settings: Any) -> None:
    global _secrets
    _secrets = tuple(value for name in ("llm_api_key", "amap_api_key", "unsplash_access_key", "unsplash_secret_key", "database_url")
                     if (value := settings.secret_value(name)))
    root = logging.getLogger()
    # Only replace our own handlers; preserve pytest/caller-installed handlers.
    for handler in list(root.handlers):
        if getattr(handler, "_trip_handler", False):
            root.removeHandler(handler)
            handler.close()
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if settings.log_file_enabled:
        directory = Path(settings.log_dir)
        directory.mkdir(parents=True, exist_ok=True)
        handlers.append(RotatingFileHandler(directory / "app.log", maxBytes=10 * 1024 * 1024,
                                           backupCount=5, encoding="utf-8"))
        errors = RotatingFileHandler(directory / "error.log", maxBytes=10 * 1024 * 1024,
                                    backupCount=5, encoding="utf-8")
        errors.setLevel(logging.ERROR)
        handlers.append(errors)
    for handler in handlers:
        handler._trip_handler = True
        handler.setFormatter(SafeFormatter(json_output=settings.log_format == "json"))
        root.addHandler(handler)
    root.setLevel(settings.log_level.upper())
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpx2").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def emit_progress(event: str, **fields: Any) -> None:
    """Emit only caller-selected operational fields, never entire graph state."""
    level = logging.WARNING if event in {"model.failed", "validation.failed", "retry.scheduled"} else logging.INFO
    logger.log(level, event, extra=fields)
    payload = {"type": event, "timestamp": datetime.now(timezone.utc).isoformat(),
               **log_context.get(), **fields}
    try:
        writer = get_stream_writer()
    except RuntimeError:
        return  # Unit tests or legacy invocation outside LangGraph.
    writer(payload)


def instrument_node(function):
    """Preserve graph function signatures while reporting start/end/failure."""
    name = function.__name__

    def begin(state):
        attempt = state.get("attempt", 0) + (1 if name == "generate_candidate" else 0)
        token = log_context.set({**log_context.get(), "node": name, "attempt": attempt})
        emit_progress("node.started", node=name, label=NODE_LABELS[name], attempt=attempt)
        return token, time.perf_counter()

    def finish(started, result):
        emit_progress("node.completed", node=name, label=NODE_LABELS[name],
                      elapsed_ms=round((time.perf_counter() - started) * 1000),
                      generation_status=result.get("generation_status"))
        return result

    if inspect.iscoroutinefunction(function):
        @functools.wraps(function)
        async def wrapped(state, *args, **kwargs):
            token, started = begin(state)
            try:
                return finish(started, await function(state, *args, **kwargs))
            except Exception as exc:
                emit_progress("node.failed", node=name, error_type=type(exc).__name__)
                logger.exception("node.exception", extra={"node": name})
                raise
            finally:
                log_context.reset(token)
    else:
        @functools.wraps(function)
        def wrapped(state, *args, **kwargs):
            token, started = begin(state)
            try:
                return finish(started, function(state, *args, **kwargs))
            except Exception as exc:
                emit_progress("node.failed", node=name, error_type=type(exc).__name__)
                logger.exception("node.exception", extra={"node": name})
                raise
            finally:
                log_context.reset(token)
    return wrapped
