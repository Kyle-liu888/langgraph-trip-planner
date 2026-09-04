"""Node implementations for the travel-planning graph."""

from __future__ import annotations

import asyncio
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.runtime import Runtime

from ..llm.structured import ainvoke_structured
from ..models.schemas import TripPlan, TripRequest
from ..planner.output import (
    create_fallback_plan,
    enrich_trip_plan_poi_details,
    extract_json_object,
    validate_trip_plan_shape,
)
from ..planner.rerank import rerank_trip_plan_candidates
from .runtime import PlannerRuntime
from .query import build_planner_query, planner_max_output_tokens
from .prompts import PLANNER_AGENT_PROMPT
from .state import PlannerState
from ..observability import emit_progress, redact


async def collect_context(
    state: PlannerState,
    runtime: Runtime[PlannerRuntime],
) -> dict[str, Any]:
    context = await asyncio.to_thread(runtime.context.context_builder.collect, TripRequest.model_validate(state["request"]))
    return {
        "planner_context": context,
        "attempt": 0,
        "candidates": [],
        "last_error": "",
        "model_metadata": {
            "provider": runtime.context.model_config.provider,
            "model": runtime.context.model_config.model,
        },
        "generation_status": "context_ready",
        "generation_message": "候选地点和天气上下文采集完成",
    }


def build_prompt(
    state: PlannerState,
    runtime: Runtime[PlannerRuntime],
) -> dict[str, Any]:
    query = build_planner_query(
        runtime.context.context_builder,
        TripRequest.model_validate(state["request"]),
        state["planner_context"],
    )
    return {
        "planner_query": query,
        "generation_status": "prompt_ready",
        "generation_message": "规划提示已构造",
    }


async def generate_candidate(
    state: PlannerState,
    runtime: Runtime[PlannerRuntime],
) -> dict[str, Any]:
    attempt = state.get("attempt", 0) + 1
    settings = runtime.context.settings
    temperature = min(
        0.95,
        runtime.context.model_config.temperature
        + (attempt - 1) * settings.planner_rerank_temperature_step,
    )
    correction = ""
    if state.get("last_error"):
        correction = (
            "\n上一次输出未通过后端校验。请重新输出完整计划并修正此问题："
            f"{state['last_error'][:800]}"
        )
    messages = [
        SystemMessage(content=PLANNER_AGENT_PROMPT),
        HumanMessage(content=state["planner_query"] + correction),
    ]

    invocation_kwargs: dict[str, Any] = {
        "max_tokens": planner_max_output_tokens(TripRequest.model_validate(state["request"])),
        "temperature": temperature,
    }
    if (
        runtime.context.model_config.provider == "deepseek"
        and runtime.context.model_config.thinking_mode == "disabled"
    ):
        invocation_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

    try:
        result = await ainvoke_structured(
            runtime.context.model,
            runtime.context.model_config,
            TripPlan,
            messages,
            text_parser=extract_json_object,
            invocation_kwargs=invocation_kwargs,
        )
    except Exception as exc:
        return {
            "attempt": attempt,
            "candidate": None,
            "last_error": redact(f"模型调用或解析失败: {exc}"),
            "generation_status": "generation_failed",
            "generation_message": f"第 {attempt} 次模型生成失败",
        }

    metadata = dict(state.get("model_metadata", {}))
    metadata.update(
        {
            "structured_strategy": result.strategy,
            "attempts": attempt,
            "usage": getattr(result.raw_message, "usage_metadata", None) or {},
        }
    )
    return {
        "attempt": attempt,
        "candidate": result.parsed.model_dump(mode="json"),
        "structured_strategy": result.strategy,
        "model_metadata": metadata,
        "last_error": "",
        "generation_status": "candidate_generated",
        "generation_message": f"第 {attempt} 个候选计划已生成",
    }


def validate_candidate(state: PlannerState) -> dict[str, Any]:
    candidate = state.get("candidate")
    if candidate is None:
        return {}
    try:
        candidate = TripPlan.model_validate(candidate)
        enrich_trip_plan_poi_details(candidate, state["planner_context"])
        validate_trip_plan_shape(candidate, TripRequest.model_validate(state["request"]), state["planner_context"])
    except Exception as exc:
        emit_progress("validation.failed", error_type=type(exc).__name__, attempt=state["attempt"])
        return {
            "candidate": None,
            "last_error": redact(str(exc)),
            "generation_status": "validation_failed",
            "generation_message": f"第 {state['attempt']} 个候选未通过校验",
        }

    candidates = [*state.get("candidates", []), {"attempt": state["attempt"], "plan": candidate.model_dump(mode="json")}]
    return {
        "candidate": None,
        "candidates": candidates,
        "last_error": "",
        "generation_status": "candidate_validated",
        "generation_message": f"已获得 {len(candidates)} 个合法候选",
    }


def route_after_validation(
    state: PlannerState,
    runtime: Runtime[PlannerRuntime],
) -> str:
    settings = runtime.context.settings
    target = 1
    if settings.planner_enable_rerank:
        target = min(settings.planner_max_attempts, settings.planner_rerank_candidate_count)
    if len(state.get("candidates", [])) >= target:
        return "select"
    if state.get("attempt", 0) >= settings.planner_max_attempts:
        return "select" if state.get("candidates") else "fallback"
    emit_progress("retry.scheduled", attempt=state.get("attempt", 0) + 1,
                  max_attempts=settings.planner_max_attempts)
    return "retry"


def select_best_candidate(state: PlannerState) -> dict[str, Any]:
    ranked = rerank_trip_plan_candidates(
        [(item["attempt"], TripPlan.model_validate(item["plan"])) for item in state["candidates"]],
        TripRequest.model_validate(state["request"]),
        state["planner_context"],
    )
    best = ranked[0]
    metadata = dict(state.get("model_metadata", {}))
    metadata["selected_attempt"] = best.attempt
    metadata["candidate_count"] = len(ranked)
    metadata["rerank_score"] = best.score
    return {
        "trip_plan": best.trip_plan.model_dump(mode="json"),
        "model_metadata": metadata,
        "generation_status": "llm_success",
        "generation_message": (
            f"{metadata.get('provider')}:{metadata.get('model')} 生成成功，"
            f"结构化策略={metadata.get('structured_strategy')}"
        ),
    }


def create_fallback(state: PlannerState) -> dict[str, Any]:
    return {
        "trip_plan": create_fallback_plan(TripRequest.model_validate(state["request"])).model_dump(mode="json"),
        "generation_status": "fallback_success",
        "generation_message": "模型生成未通过校验，已返回确定性兜底计划；这不是模型生成的完整结果。",
    }
