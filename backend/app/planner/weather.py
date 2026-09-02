"""Planner 天气规范化逻辑。"""

from typing import Any, Dict, List

from ..models.schemas import TripRequest
from .dates import trip_date_strings, unknown_weather_row


def normalize_weather(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """规范化高德天气预报。"""
    forecasts = raw.get("forecasts") or []
    if not forecasts:
        return []

    rows = []
    for item in forecasts[0].get("casts", []):
        rows.append(
            {
                "date": item.get("date", ""),
                "day_weather": item.get("dayweather", ""),
                "night_weather": item.get("nightweather", ""),
                "day_temp": parse_temperature_value(item.get("daytemp")),
                "night_temp": parse_temperature_value(item.get("nighttemp")),
                "wind_direction": item.get("daywind", ""),
                "wind_power": item.get("daypower", ""),
                "source": "amap_forecast",
            }
        )
    return rows


def align_trip_weather(request: TripRequest, available_weather: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """只把日期真实命中的天气用于行程日期，远期日期保持未知。"""
    by_date = {item.get("date"): item for item in available_weather}
    rows = []
    for date_text in trip_date_strings(request):
        if date_text in by_date:
            rows.append(by_date[date_text])
        else:
            rows.append(unknown_weather_row(date_text))
    return rows


def parse_temperature_value(value: Any) -> Any:
    """高德天气温度能转数字就转数字，否则保留未知表达。"""
    if value is None:
        return "未知"
    text = str(value).replace("°C", "").replace("℃", "").replace("°", "").strip()
    return int(text) if text.lstrip("-").isdigit() else (text or "未知")
