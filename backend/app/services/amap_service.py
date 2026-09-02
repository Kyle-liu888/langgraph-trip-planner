"""Direct Amap HTTP service; no agent framework or MCP process is required."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from ..config import get_settings
from ..models.schemas import Location, POIInfo, WeatherInfo
from ..planner.amap import AmapPlannerClient


class AmapService:
    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or get_settings().secret_value("amap_api_key")
        if not key:
            raise ValueError("AMAP_API_KEY 未配置")
        self.client = AmapPlannerClient(key)

    def search_poi(self, keywords: str, city: str, citylimit: bool = True) -> list[POIInfo]:
        rows = self.client.search_keywords(
            city=city,
            keywords=[keywords],
            source_role="scenic",
            limit=10,
            require_location=True,
            source_bucket="api_search",
        )
        return [
            POIInfo(
                id=str(row.get("id") or ""),
                name=str(row.get("name") or ""),
                type=str(row.get("type") or row.get("category") or "POI"),
                address=str(row.get("address") or ""),
                location=Location.model_validate(row["location"]),
                tel=str(row.get("tel") or "") or None,
            )
            for row in rows
            if row.get("location")
        ]

    def get_weather(self, city: str) -> list[WeatherInfo]:
        data = self.client.get("/weather/weatherInfo", {"city": city, "extensions": "all"})
        forecasts = data.get("forecasts") or []
        casts = forecasts[0].get("casts", []) if forecasts else []
        return [
            WeatherInfo(
                date=str(row.get("date") or ""),
                day_weather=str(row.get("dayweather") or ""),
                night_weather=str(row.get("nightweather") or ""),
                day_temp=row.get("daytemp") or "未知",
                night_temp=row.get("nighttemp") or "未知",
                wind_direction=str(row.get("daywind") or ""),
                wind_power=str(row.get("daypower") or ""),
            )
            for row in casts
        ]

    def geocode(self, address: str, city: str | None = None) -> Location | None:
        data = self.client.get("/geocode/geo", {"address": address, "city": city})
        rows = data.get("geocodes") or []
        if not rows:
            return None
        longitude, latitude = str(rows[0].get("location") or "").split(",", 1)
        return Location(longitude=float(longitude), latitude=float(latitude))

    def plan_route(
        self,
        origin_address: str,
        destination_address: str,
        origin_city: str | None = None,
        destination_city: str | None = None,
        route_type: str = "walking",
    ) -> dict[str, Any]:
        origin = self.geocode(origin_address, origin_city)
        destination = self.geocode(destination_address, destination_city)
        if not origin or not destination:
            raise ValueError("无法解析起点或终点地址")
        endpoints = {
            "walking": "/direction/walking",
            "driving": "/direction/driving",
            "transit": "/direction/transit/integrated",
        }
        path = endpoints.get(route_type, endpoints["walking"])
        data = self.client.get(
            path,
            {
                "origin": f"{origin.longitude},{origin.latitude}",
                "destination": f"{destination.longitude},{destination.latitude}",
                "city": origin_city,
                "cityd": destination_city,
            },
        )
        route = data.get("route") or {}
        options = route.get("transits") if route_type == "transit" else route.get("paths")
        first = (options or [{}])[0]
        distance = float(first.get("distance") or route.get("distance") or 0)
        duration = int(float(first.get("duration") or 0))
        return {
            "distance": distance,
            "duration": duration,
            "route_type": route_type,
            "description": f"{route_type} 路线，全程约 {distance / 1000:.1f} 公里",
        }

    def get_poi_detail(self, poi_id: str) -> dict[str, Any]:
        data = self.client.get("/place/detail", {"id": poi_id, "extensions": "all"})
        rows = data.get("pois") or []
        return rows[0] if rows else {}


@lru_cache(maxsize=1)
def get_amap_service() -> AmapService:
    return AmapService()
