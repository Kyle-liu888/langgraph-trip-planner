"""Planner 路线时间 hint 构造。"""

import math
from typing import Any, Dict, List

from ..models.schemas import TripRequest


def build_route_hints(
    request: TripRequest,
    planner_context: Dict[str, Any],
    limit: int,
) -> List[Dict[str, Any]]:
    """构造关键候选之间的路线时间提示。

    第一版只做直线距离估算，不调用路线API；这样不会额外消耗高德额度。
    后续如果接入高德路线API，只需要把source从haversine_estimated升级即可。
    """
    snapshot = planner_context.get("tool_snapshot", {})
    hotels = [item for item in (snapshot.get("hotel_pois") or []) if item.get("location")][:3]
    scenic = dedupe_pois(
        (snapshot.get("classic_pois") or [])
        + (snapshot.get("preference_pois") or [])
        + (snapshot.get("scenic_pois") or [])
        + (snapshot.get("experience_pois") or [])
    )
    scenic = [item for item in scenic if item.get("location")][:8]

    hints = []
    for hotel in hotels:
        for poi in scenic[:4]:
            hints.append(route_hint(hotel, "hotel_pois", poi, poi.get("source_bucket") or "scenic_pois", request))

    for index, origin in enumerate(scenic[:6]):
        for destination in scenic[index + 1:6]:
            hints.append(route_hint(origin, origin.get("source_bucket") or "scenic_pois", destination, destination.get("source_bucket") or "scenic_pois", request))

    return hints[:limit]


def route_hint(
    origin: Dict[str, Any],
    origin_bucket: str,
    destination: Dict[str, Any],
    destination_bucket: str,
    request: TripRequest,
) -> Dict[str, Any]:
    """根据两个POI构造路线时间估算。"""
    distance_km = haversine_km(origin.get("location") or {}, destination.get("location") or {})
    estimated_minutes = estimate_route_minutes(distance_km, request.transportation)
    return {
        "origin_name": origin.get("name", ""),
        "origin_bucket": origin_bucket,
        "destination_name": destination.get("name", ""),
        "destination_bucket": destination_bucket,
        "transport_mode": request.transportation,
        "estimated_minutes": estimated_minutes,
        "distance_km": round(distance_km, 1),
        "source": "haversine_estimated",
        "confidence": "medium",
    }


def haversine_km(left: Dict[str, Any], right: Dict[str, Any]) -> float:
    """计算两个经纬度点的直线距离。"""
    if not left or not right:
        return 0.0
    lon1 = math.radians(float(left.get("longitude", 0)))
    lat1 = math.radians(float(left.get("latitude", 0)))
    lon2 = math.radians(float(right.get("longitude", 0)))
    lat2 = math.radians(float(right.get("latitude", 0)))
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(value))


def estimate_route_minutes(distance_km: float, transportation: str) -> int:
    """按交通方式把直线距离转成保守分钟数。"""
    if distance_km <= 0:
        return 0
    if "步行" in transportation:
        speed = 4.0
        overhead = 5
    elif "自驾" in transportation or "打车" in transportation:
        speed = 25.0
        overhead = 15
    else:
        speed = 18.0
        overhead = 18
    # 直线距离乘1.35，粗略模拟道路绕行。
    return int(math.ceil((distance_km * 1.35 / speed) * 60 + overhead))


def dedupe_pois(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按名称去重。"""
    seen = set()
    results = []
    for row in rows:
        name = row.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        results.append(row)
    return results
