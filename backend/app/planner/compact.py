"""Planner 输入压缩逻辑。"""

from typing import Any, Dict, List


def compact_for_planner(planner_context: Dict[str, Any]) -> Dict[str, Any]:
    """把原始工具快照压缩成模型真正需要看的 Planner 输入。"""
    snapshot = planner_context.get("tool_snapshot", {})
    return {
        "version": planner_context.get("version", "planner_context"),
        "request": planner_context.get("request", {}),
        "party": planner_context.get("party", {}),
        "budget_constraint": planner_context.get("budget_constraint", {}),
        "preference_profile": planner_context.get("preference_profile", {}),
        "lodging_policy": planner_context.get("lodging_policy", {}),
        "pricing_policy": planner_context.get("pricing_policy", {}),
        "route_policy": planner_context.get("route_policy", {}),
        "tool_snapshot": {
            "trip_weather": compact_weather(snapshot.get("trip_weather") or []),
            "classic_pois": compact_pois(snapshot.get("classic_pois") or []),
            "preference_pois": compact_pois(snapshot.get("preference_pois") or []),
            "scenic_pois": compact_pois(snapshot.get("scenic_pois") or []),
            "experience_pois": compact_pois(snapshot.get("experience_pois") or []),
            "hotel_pois": compact_pois(snapshot.get("hotel_pois") or []),
            "food_pois": compact_pois(snapshot.get("food_pois") or []),
            "food_query_groups": compact_food_query_groups(snapshot.get("food_query_groups") or []),
            "route_hints": compact_route_hints(snapshot.get("route_hints") or []),
            "candidate_counts": {
                "classic_pois": len(snapshot.get("classic_pois") or []),
                "preference_pois": len(snapshot.get("preference_pois") or []),
                "scenic_pois": len(snapshot.get("scenic_pois") or []),
                "experience_pois": len(snapshot.get("experience_pois") or []),
                "hotel_pois": len(snapshot.get("hotel_pois") or []),
                "food_pois": len(snapshot.get("food_pois") or []),
                "food_query_groups": len(snapshot.get("food_query_groups") or []),
                "route_hints": len(snapshot.get("route_hints") or []),
            },
        },
        "planner_constraints": planner_context.get("planner_constraints", {}),
    }


def compact_weather(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """裁剪天气字段，只保留生成 weather_info 需要的内容。"""
    keys = ["date", "day_weather", "night_weather", "day_temp", "night_temp", "wind_direction", "wind_power", "source"]
    return [
        {key: item.get(key) for key in keys if item.get(key) not in (None, "")}
        for item in rows
    ]


def compact_pois(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """裁剪 POI 字段，只保留规划、展示和预算估算需要的信息。"""
    results = []
    for item in rows:
        compact = {
            "name": item.get("name", ""),
            "type": compact_type(item.get("type", "")),
            "district": item.get("adname", ""),
            "address": short_text(item.get("address", ""), 48),
            "location": item.get("location"),
            "rating": item.get("rating", ""),
            "cost": item.get("cost", ""),
            "estimated_cost_hint": item.get("estimated_cost_hint"),
            "ticket_price_hint": item.get("ticket_price_hint"),
            "ticket_price_season": item.get("ticket_price_season"),
            "meal_cost_hint": item.get("meal_cost_hint"),
            "cost_unit": item.get("cost_unit"),
            "cost_source": item.get("cost_source") or item.get("ticket_price_source"),
            "ticket_price_source": item.get("ticket_price_source"),
            "meal_roles": item.get("meal_roles"),
            "cuisine_tags": item.get("cuisine_tags"),
            "diet_tags": item.get("diet_tags"),
            "avoid_risk_keywords": item.get("avoid_risk_keywords"),
            "price_level": item.get("price_level"),
            "matched_keyword": item.get("source_keyword", ""),
            "source_bucket": item.get("source_bucket", ""),
        }
        results.append(drop_empty_values(compact))
    return results


def compact_food_query_groups(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """保留餐饮召回分桶，方便 Planner 理解 food_pois 覆盖面。"""
    results = []
    for item in rows:
        compact = {
            "bucket": item.get("bucket", ""),
            "keywords": item.get("keywords") or [],
        }
        results.append(drop_empty_values(compact))
    return results


def compact_route_hints(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """裁剪路线提示字段。"""
    keys = [
        "origin_name",
        "origin_bucket",
        "destination_name",
        "destination_bucket",
        "transport_mode",
        "estimated_minutes",
        "distance_km",
        "source",
        "confidence",
    ]
    return [
        {key: item.get(key) for key in keys if item.get(key) not in (None, "")}
        for item in rows
    ]


def compact_type(value: Any) -> str:
    """高德 type 往往很长，只取最能给 Planner 提示用途的部分。"""
    text = str(value or "")
    if "|" in text:
        text = text.split("|", 1)[0]
    parts = [part for part in text.split(";") if part]
    return ";".join(parts[-2:]) if len(parts) >= 2 else text


def short_text(value: Any, max_chars: int) -> str:
    """避免超长地址或异常文本撑大 Planner 输入。"""
    text = str(value or "").strip()
    return text if len(text) <= max_chars else f"{text[:max_chars]}..."


def drop_empty_values(item: Dict[str, Any]) -> Dict[str, Any]:
    """删除空值字段，让 prompt 更短。"""
    return {
        key: value
        for key, value in item.items()
        if value not in (None, "", [], {})
    }
