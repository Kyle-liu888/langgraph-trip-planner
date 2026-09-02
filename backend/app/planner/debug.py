"""Planner 命令行预览逻辑。"""

import os
from typing import Any, Dict, List


PLANNER_CONTEXT_PRINT_LIMIT = int(os.getenv("PLANNER_CONTEXT_PRINT_LIMIT", "8"))


def print_summary(planner_context: Dict[str, Any]) -> None:
    """打印结构化工具快照摘要。"""
    snapshot = planner_context.get("tool_snapshot", {})
    status = snapshot.get("tool_status", {})
    print(
        "工具快照: "
        f"经典={len(snapshot.get('classic_pois') or [])}, "
        f"偏好={len(snapshot.get('preference_pois') or [])}, "
        f"体验={len(snapshot.get('experience_pois') or [])}, "
        f"酒店={len(snapshot.get('hotel_pois') or [])}, "
        f"餐饮={len(snapshot.get('food_pois') or [])}, "
        f"路线={len(snapshot.get('route_hints') or [])}, "
        f"天气={len(snapshot.get('trip_weather') or [])}"
    )
    for name, item in status.items():
        print(f"  - {name}: {'ok' if item.get('ok') else 'failed'} | {item.get('message')}")
    print()


def print_visualization(planner_context: Dict[str, Any], limit: int = PLANNER_CONTEXT_PRINT_LIMIT) -> None:
    """在命令行打印步骤1工具快照明细，便于直接审查。"""
    snapshot = planner_context.get("tool_snapshot", {})
    print("=" * 60)
    print("PlannerContext 明细预览")
    print("=" * 60)
    print_weather_rows(snapshot.get("trip_weather") or [])
    print_poi_rows("城市经典 classic_pois", snapshot.get("classic_pois") or [], limit)
    print_poi_rows("偏好景点 preference_pois", snapshot.get("preference_pois") or [], limit)
    print_poi_rows("景点合并 scenic_pois", snapshot.get("scenic_pois") or [], limit)
    print_poi_rows("体验候选 experience_pois", snapshot.get("experience_pois") or [], limit)
    print_poi_rows("酒店候选 hotel_pois", snapshot.get("hotel_pois") or [], limit)
    print_poi_rows("餐饮候选 food_pois", snapshot.get("food_pois") or [], limit)
    print_route_rows("路线提示 route_hints", snapshot.get("route_hints") or [], limit)
    print("=" * 60)
    print()


def print_weather_rows(rows: List[Dict[str, Any]]) -> None:
    """打印行程天气。"""
    print("行程天气 trip_weather:")
    if not rows:
        print("  (empty)")
        return
    for item in rows:
        print(
            "  - "
            f"{item.get('date')} | "
            f"{item.get('day_weather')}/{item.get('night_weather')} | "
            f"{item.get('day_temp')}/{item.get('night_temp')} | "
            f"{item.get('wind_direction')} {item.get('wind_power')} | "
            f"{item.get('source')}"
        )
    print()


def print_poi_rows(title: str, rows: List[Dict[str, Any]], limit: int) -> None:
    """打印POI候选预览。"""
    print(f"{title}: total={len(rows)}, showing={min(len(rows), limit)}")
    if not rows:
        print("  (empty)")
        print()
        return

    for index, item in enumerate(rows[:limit], start=1):
        location = item.get("location") or {}
        location_text = ""
        if location:
            location_text = f"{location.get('longitude')},{location.get('latitude')}"
        hints = []
        if item.get("estimated_cost_hint") is not None:
            hints.append(f"hotel_hint={item.get('estimated_cost_hint')}({item.get('cost_source', '')})")
        if item.get("ticket_price_hint") is not None:
            hints.append(f"ticket_hint={item.get('ticket_price_hint')}({item.get('ticket_price_source', '')})")
        if item.get("meal_cost_hint") is not None:
            hints.append(f"meal_hint={item.get('meal_cost_hint')}({item.get('cost_source', '')})")
        if item.get("high_end_verified"):
            hints.append("high_end=verified")
        elif item.get("high_end_estimated"):
            hints.append("high_end=estimated")
        if item.get("budget_filter_relaxed"):
            hints.append("budget_filter=relaxed")
        if item.get("budget_rank") is not None:
            hints.append(f"budget_rank={item.get('budget_rank')}")
        print(
            "  - "
            f"#{index} {item.get('name', '')} | "
            f"type={item.get('type', '')} | "
            f"addr={item.get('address', '')} | "
            f"ad={item.get('adname', '')} | "
            f"loc={location_text or '无'} | "
            f"rating={item.get('rating', '')} | "
            f"cost={item.get('cost', '')} | "
            f"keyword={item.get('source_keyword', '')} | "
            f"bucket={item.get('source_bucket', '')}"
            f"{' | ' + '; '.join(hints) if hints else ''}"
        )
    print()


def print_route_rows(title: str, rows: List[Dict[str, Any]], limit: int) -> None:
    """打印路线时间提示。"""
    print(f"{title}: total={len(rows)}, showing={min(len(rows), limit)}")
    if not rows:
        print("  (empty)")
        print()
        return

    for index, item in enumerate(rows[:limit], start=1):
        print(
            "  - "
            f"#{index} {item.get('origin_name', '')} -> {item.get('destination_name', '')} | "
            f"mode={item.get('transport_mode', '')} | "
            f"minutes={item.get('estimated_minutes', '')} | "
            f"distance={item.get('distance_km', '')}km | "
            f"source={item.get('source', '')}"
        )
    print()
