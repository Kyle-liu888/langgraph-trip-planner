"""Planner 输入构造和输出 token 预算。"""

import json
import os
from typing import Any, Dict

from ..models.schemas import TripRequest
from ..observability import emit_progress


PLANNER_OUTPUT_BASE_TOKENS = int(os.getenv("PLANNER_OUTPUT_BASE_TOKENS", "3000"))
PLANNER_OUTPUT_TOKENS_PER_DAY = int(os.getenv("PLANNER_OUTPUT_TOKENS_PER_DAY", "1800"))
PLANNER_MAX_OUTPUT_TOKENS_CAP = int(os.getenv("PLANNER_MAX_OUTPUT_TOKENS_CAP", "16000"))


def build_planner_query(planner_context_builder: Any, request: TripRequest, planner_context: Dict[str, Any]) -> str:
    """Keep all user constraints; avoid repeating the complete system rules."""
    prompt_context = planner_context_builder.compact_for_planner(planner_context)
    context_json = json.dumps(prompt_context, ensure_ascii=False, separators=(",", ":"))
    emit_progress("prompt.compacted",
                  original_chars=len(json.dumps(planner_context, ensure_ascii=False, separators=(",", ":"))),
                  compact_chars=len(context_json))
    return f"""请根据以下 PlannerContext 生成{request.city}的{request.travel_days}天旅行计划。
PlannerContext:
{context_json}

严格遵守系统提示中的 TripPlan JSON 结构、价格复制、预算汇总、餐饮去重和住宿规则。
顶层 city 必须逐字复制 request.city，不要改写地名、增加或删去“市”字；起止日期必须与请求一致。
只输出完整 JSON，不输出解释或 Markdown。每天包含 1–3 个真实景点和完整三餐。
所有用户偏好、忌口和额外要求以 request、preference_profile 及 planner_constraints 为准。
description 用简短完整句子，避免重复地址和价格；保留必要的交通解释。不要省略必需字段。
"""


def planner_max_output_tokens(request: TripRequest) -> int:
    """按行程天数动态估算 Planner 输出上限。"""
    return min(
        PLANNER_OUTPUT_BASE_TOKENS + request.travel_days * PLANNER_OUTPUT_TOKENS_PER_DAY,
        PLANNER_MAX_OUTPUT_TOKENS_CAP,
    )
