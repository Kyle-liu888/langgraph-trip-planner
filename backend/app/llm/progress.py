"""Bounded model calls and content-free streaming progress across providers."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler

from ..observability import emit_progress


class ModelRequestTimeout(TimeoutError):
    """The complete model invocation exceeded its budget (including SDK retries)."""


def error_details(exc: BaseException) -> dict[str, Any]:
    chain, current = [], exc
    while current is not None and len(chain) < 6:
        chain.append(type(current).__name__)
        current = current.__cause__ or current.__context__
    names = " ".join(chain).lower()
    status = getattr(exc, "status_code", None)
    if isinstance(exc, TimeoutError) or "timeout" in names:
        code, label = "MODEL_TIMEOUT", "模型请求超时"
    elif status == 429:
        code, label = "MODEL_RATE_LIMIT", "模型服务限流"
    elif "connection" in names or "connecterror" in names:
        code, label = "MODEL_CONNECTION_ERROR", "模型服务连接失败"
    elif status in (401, 403):
        code, label = "MODEL_AUTH_ERROR", "模型服务认证失败，请检查配置"
    elif isinstance(status, int) and status >= 500:
        code, label = "MODEL_SERVICE_ERROR", "模型服务暂时不可用"
    else:
        code, label = "MODEL_OUTPUT_ERROR", "模型调用或输出解析失败"
    return {"error_code": code, "label": label, "error_type": type(exc).__name__,
            "cause_types": chain, **({"http_status": status} if isinstance(status, int) else {})}


class ModelProgress(AsyncCallbackHandler):
    run_inline = True

    def __init__(self, fields: dict, started: float):
        self.fields, self.started = fields, started
        self.chunks = self.characters = 0
        self.last_report = 0.0

    async def on_llm_new_token(self, token, *, chunk=None, **kwargs):
        self.chunks += 1
        # Count only final-answer text. Never emit content, tool arguments or reasoning.
        content = getattr(getattr(chunk, "message", None), "content", "")
        if isinstance(content, str):
            self.characters += len(content)
        now = time.perf_counter()
        if self.chunks == 1 or now - self.last_report >= 2:
            self.last_report = now
            emit_progress("model.progress", **self.fields, response_chunks=self.chunks,
                          output_chars=self.characters, elapsed_ms=round((now - self.started) * 1000),
                          label=f"正在接收模型响应，已收到 {self.characters} 字符行程正文")


async def invoke_with_progress(runnable, messages, kwargs, config, fields):
    started = time.perf_counter()
    callback = ModelProgress(fields, started)
    task = asyncio.create_task(runnable.ainvoke(messages, config={"callbacks": [callback]}, **kwargs))
    try:
        async with asyncio.timeout(config.timeout):
            while True:
                done, _ = await asyncio.wait({task}, timeout=config.progress_interval)
                if done:
                    return task.result()
                emit_progress("model.waiting", **fields,
                              elapsed_ms=round((time.perf_counter() - started) * 1000),
                              response_chunks=callback.chunks, output_chars=callback.characters,
                              timeout_seconds=config.timeout,
                              label="仍在等待完整行程" if callback.chunks else "请求仍在等待模型响应")
    except TimeoutError as exc:
        raise ModelRequestTimeout("模型调用超过时间预算") from exc
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)
