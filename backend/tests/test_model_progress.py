"""Slow and streamed model responses are simulated; no provider API is called."""
import asyncio
import json
from unittest.mock import patch

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_deepseek import ChatDeepSeek
from pydantic import BaseModel

from app.llm.config import ModelConfig
from app.llm.progress import ModelRequestTimeout, error_details
from app.llm.structured import ainvoke_structured


class Answer(BaseModel):
    answer: str


async def invoke(model, config):
    return await ainvoke_structured(model, config, Answer, [HumanMessage(content="private prompt")],
                                   text_parser=json.loads)


def test_slow_request_reports_waiting_times_out_and_cancels_work():
    async def scenario():
        cancelled = asyncio.Event()

        class Slow:
            async def ainvoke(self, *args, **kwargs):
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.set()

        config = ModelConfig(provider="fake", model="slow", timeout=.08, progress_interval=.01)
        with patch("app.llm.progress.emit_progress") as progress, patch("app.llm.structured.emit_progress") as events:
            with pytest.raises(ModelRequestTimeout):
                await invoke(Slow(), config)
            assert cancelled.is_set()
            assert any(call.args[0] == "model.waiting" for call in progress.call_args_list)
            failure = next(call.kwargs for call in events.call_args_list if call.args[0] == "model.failed")
            assert failure["error_code"] == "MODEL_TIMEOUT"
            assert failure["elapsed_ms"] >= 50
            assert "private prompt" not in str(events.call_args_list + progress.call_args_list)
    asyncio.run(scenario())


def test_outer_cancellation_stops_inflight_request_without_retry():
    async def scenario():
        started, cancelled = asyncio.Event(), asyncio.Event()

        class Slow:
            async def ainvoke(self, *args, **kwargs):
                started.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.set()

        with patch("app.llm.structured.emit_progress") as events:
            task = asyncio.create_task(invoke(Slow(), ModelConfig(provider="fake", model="slow")))
            await started.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert cancelled.is_set()
            kinds = [call.args[0] for call in events.call_args_list]
            assert kinds == ["model.started", "model.cancelled"]
    asyncio.run(scenario())


def test_real_deepseek_adapter_aggregates_mock_stream_and_emits_only_counts():
    async def scenario():
        requests = []

        def respond(request):
            body = json.loads(request.content)
            requests.append(body)
            assert body["stream"] is True
            assert body["response_format"] == {"type": "json_object"}
            deltas = [{"role": "assistant", "reasoning_content": "private reasoning"},
                      {"content": '{"answer":"'}, {"content": 'private result"}'}]
            data = "".join("data: " + json.dumps({
                "id": "mock", "object": "chat.completion.chunk", "created": 0, "model": "mock",
                "choices": [{"index": 0, "delta": delta, "finish_reason": None}]
            }) + "\n\n" for delta in deltas)
            return httpx.Response(200, headers={"content-type": "text/event-stream"},
                                  content=data + 'data: [DONE]\n\n')

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            model = ChatDeepSeek(model="mock", api_key="test-only", streaming=True,
                                 max_retries=0, http_async_client=client)
            with patch("app.llm.progress.emit_progress") as progress, patch("app.llm.structured.emit_progress") as events:
                result = await invoke(model, ModelConfig(provider="deepseek", model="mock"))
                assert result.parsed.answer == "private result"
                assert len(requests) == 1
                assert any(call.args[0] == "model.progress" for call in progress.call_args_list)
                recorded = str(events.call_args_list + progress.call_args_list)
                assert all(secret not in recorded for secret in ("private prompt", "private reasoning", "private result"))
    asyncio.run(scenario())


def test_connection_error_classification_does_not_include_credentials():
    error = httpx.ConnectError("failed https://user:password@example.test")
    detail = error_details(error)
    assert detail["error_code"] == "MODEL_CONNECTION_ERROR"
    assert "password" not in json.dumps(detail)


def test_non_streaming_provider_still_completes_with_waiting_feedback():
    async def scenario():
        class Delayed:
            async def ainvoke(self, *args, **kwargs):
                await asyncio.sleep(.03)
                return AIMessage(content='{"answer":"ok"}')
        with patch("app.llm.progress.emit_progress") as progress:
            result = await invoke(Delayed(), ModelConfig(provider="custom", model="custom", progress_interval=.01))
            assert result.parsed.answer == "ok"
            assert any(call.args[0] == "model.waiting" for call in progress.call_args_list)
    asyncio.run(scenario())
