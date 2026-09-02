"""Planner 顶层协议字段和策略字段构造逻辑。"""

from datetime import datetime, timezone
import re
from typing import Any, Dict, List

from ..models.schemas import TripRequest
from .dates import trip_date_strings, unknown_weather_row
from .pois import infer_food_constraints, infer_pace, positive_preference_tags, unique_strings


NEGATIVE_CONSTRAINT_PHRASES = [
    "人挤人的网红店",
    "网红排队店",
    "过度商业化景点",
    "大型商场",
    "纯购物行程",
    "夜生活",
    "过长步行",
    "长时间排队",
    "打卡式景点",
    "高价餐厅",
    "景区快餐",
    "太早起",
    "密集行程",
    "太偏远的景点",
    "太累的路线",
    "购物团",
    "跟团游",
    "爬山",
    "酒吧",
]

BUDGET_USAGE_RATIO_BY_LEVEL = {
    "limited": (0.72, 1.00),
    "standard": (0.60, 1.05),
    "comfortable": (0.70, 1.10),
    "premium": (0.75, 1.12),
    "luxury": (0.75, 1.18),
}


def build_empty_context(request: TripRequest) -> Dict[str, Any]:
    """创建空 PlannerContext，工具失败时也保持输入协议稳定。"""
    return {
        "version": "planner_context",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "request": request_payload(request),
        "party": request.party.model_dump(),
        "budget_constraint": request.budget_constraint.model_dump(),
        "preference_profile": build_preference_profile(request),
        "lodging_policy": build_lodging_policy(request),
        "pricing_policy": build_pricing_policy(),
        "route_policy": build_route_policy(request),
        "tool_snapshot": {
            "classic_pois": [],
            "preference_pois": [],
            "scenic_pois": [],
            "experience_pois": [],
            "hotel_pois": [],
            "food_pois": [],
            "food_query_groups": [],
            "route_hints": [],
            "available_weather": [],
            "trip_weather": unknown_trip_weather(request),
            "tool_status": {},
        },
        "planner_constraints": {
            "days_count": request.travel_days,
            "expected_dates": trip_date_strings(request),
            "attractions_per_day": "1-3",
            "meals_per_day": ["breakfast", "lunch", "dinner"],
            "weather_policy": (
                "只能使用trip_weather。天气不可用的日期必须写远期天气暂无准确预报，"
                "温度写未知，不要把短期天气平移到未来日期。"
            ),
            "grounding_policy": (
                "景点、体验、酒店、餐饮优先来自tool_snapshot候选；lunch/dinner必须来自food_pois。"
                "价格字段必须复制候选里的hint；确需补充常识时，要保持城市匹配并避免精确坐标编造。"
            ),
            "route_policy": (
                "当前版本不提供路线hint；请根据候选POI的district、address和location"
                "自行安排顺路组合，避免明显跨区跳跃。"
            ),
            "budget_fit_policy": build_budget_fit_policy(request),
        },
    }


def unknown_trip_weather(request: TripRequest) -> List[Dict[str, Any]]:
    """生成每一天的未知天气占位，保证协议稳定。"""
    return [unknown_weather_row(date_text) for date_text in trip_date_strings(request)]


def request_payload(request: TripRequest) -> Dict[str, Any]:
    """PlannerContext.request只保留原始旅行字段，结构化字段放顶层。"""
    return request.model_dump(exclude={"party", "budget_constraint"})


def build_preference_profile(request: TripRequest) -> Dict[str, Any]:
    """把偏好、自由文本拆成正向偏好和负向约束。"""
    food_constraints = infer_food_constraints(request)
    text = request.free_text_input or ""
    negative_constraints = list(food_constraints["avoid"])
    negative_constraints.extend(extract_negative_constraints(text))

    traveler_constraints = {
        "needs_child_friendly": request.party.children > 0 or "带娃" in text or "孩子" in text,
        "needs_elder_friendly": request.party.elders > 0 or "老人" in text or "长辈" in text,
        "avoid_long_walk": any(marker in text for marker in ["少走路", "不想太累", "行动不便", "无障碍", "轮椅"]),
    }

    return {
        "positive_preferences": positive_preference_tags(request),
        "negative_constraints": unique_strings(negative_constraints),
        "pace": infer_pace(request),
        "diet_positive": [] if food_constraints["diet"] == "无" else [food_constraints["diet"]],
        "diet_avoid": food_constraints["avoid"],
        "traveler_constraints": traveler_constraints,
    }


def extract_negative_constraints(text: str) -> List[str]:
    """从自由文本中抽取负向约束短语。

    这里不是做复杂NLP，只把高频、会影响规划质量的约束显式化。
    """
    results = []
    for phrase in NEGATIVE_CONSTRAINT_PHRASES:
        if phrase in text:
            results.append(phrase)

    for marker in ["尽量避开", "避开", "避免", "不要安排", "不要", "不想"]:
        for part in re.findall(rf"{marker}([^。；;，,]+)", text):
            for item in re.split(r"[、/和及与]", part):
                item = item.strip(" ：:，,。；;")
                if 1 < len(item) <= 12:
                    results.append(item)
    return unique_strings(results)


def build_lodging_policy(request: TripRequest) -> Dict[str, Any]:
    """住宿晚数规则。"""
    return {
        "hotel_cost_unit": "per_night",
        "default_lodging_nights": max(request.travel_days - 1, 0),
        "last_day_hotel_default": None,
    }


def build_pricing_policy() -> Dict[str, Any]:
    """统一预算口径。"""
    return {
        "currency": "CNY",
        "hotel_cost_unit": "per_night",
        "attraction_ticket_unit": "adult_ticket",
        "meal_cost_unit": "per_person_per_meal",
        "transportation_cost_unit": "party_total_per_day",
    }


def build_route_policy(request: TripRequest) -> Dict[str, Any]:
    """当前动线策略。"""
    return {
        "transportation_mode": request.transportation,
        "route_hint_status": "disabled",
        "route_basis": ["poi_district", "poi_address", "poi_location"],
        "future_enhancement": "amap_route_api_with_cache",
    }


def build_budget_fit_policy(request: TripRequest) -> Dict[str, Any]:
    """把预算档位转换成 Planner 可执行的目标花费区间。

    这里不是要求模型精确花光预算，而是避免高预算样本被规划成
    明显低配方案。hard 预算不应超过用户上限；soft 预算允许轻微
    上浮，但仍要贴近用户档位。
    """
    constraint = request.budget_constraint
    amount = int(constraint.amount or 0)
    if amount <= 0 or constraint.strictness == "none":
        return {
            "enabled": False,
            "reason": "budget_amount_unavailable_or_none_strictness",
        }

    min_ratio, max_ratio = BUDGET_USAGE_RATIO_BY_LEVEL.get(
        constraint.budget_level,
        BUDGET_USAGE_RATIO_BY_LEVEL["standard"],
    )
    if constraint.strictness == "hard":
        max_ratio = min(max_ratio, 1.0)
    elif constraint.strictness == "soft":
        max_ratio = max(max_ratio, 1.05)

    return {
        "enabled": True,
        "budget_level": constraint.budget_level,
        "strictness": constraint.strictness,
        "amount": amount,
        "target_min_ratio": min_ratio,
        "target_max_ratio": max_ratio,
        "target_min_total": int(round(amount * min_ratio / 100.0) * 100),
        "target_max_total": int(round(amount * max_ratio / 100.0) * 100),
        "instruction": "budget.total应尽量落在target_min_total和target_max_total之间；不要为了省钱显著低于预算档位。",
    }
