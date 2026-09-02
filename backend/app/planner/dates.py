"""Planner 日期和天气占位工具。"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..models.schemas import TripRequest


def trip_date_strings(request: TripRequest) -> List[str]:
    """根据start_date和travel_days生成行程日期。"""
    start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
    return [(start_date + timedelta(days=index)).strftime("%Y-%m-%d") for index in range(request.travel_days)]


def unknown_weather_row(date_text: str) -> Dict[str, Any]:
    """远期天气不可用时的显式表达。"""
    return {
        "date": date_text,
        "day_weather": "远期天气暂无准确预报",
        "night_weather": "远期天气暂无准确预报",
        "day_temp": "未知",
        "night_temp": "未知",
        "wind_direction": "未知",
        "wind_power": "未知",
        "source": "unavailable_future_weather",
    }
