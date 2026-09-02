"""Planner 价格 hint 规则。

这里的价格不是实时交易价，而是给 Planner 和训练数据使用的稳定预算口径。
"""

import json
import os
from datetime import datetime
from functools import lru_cache
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from ..models.schemas import TripRequest
from .output import normalize_poi_name as normalize_planner_poi_name


HOTEL_BASE_COST_BY_TYPE = [
    (["豪华", "奢华", "五星"], 1200),
    (["高端"], 750),
    (["亲子"], 520),
    (["舒适", "中端", "精品"], 420),
    (["民宿"], 300),
    (["经济", "快捷", "青年"], 220),
]
HOTEL_CITY_FACTORS = {
    "北京": 1.15,
    "上海": 1.15,
    "三亚": 1.15,
    "杭州": 1.15,
    "广州": 1.05,
    "深圳": 1.05,
    "成都": 1.05,
    "西安": 1.05,
    "青岛": 1.05,
    "厦门": 1.05,
    "南京": 1.05,
    "苏州": 1.05,
}
HOTEL_FALLBACK_CAP_BY_BUDGET_LEVEL = {
    "comfortable": 700,
}
HIGH_END_HOTEL_FALLBACK_BY_SIGNAL = [
    (
        [
            "丽思卡尔顿",
            "华尔道夫",
            "柏悦",
            "宝格丽",
            "文华东方",
            "安缦",
            "瑰丽",
            "瑞吉",
            "四季",
            "半岛",
            "康莱德",
            "奢华",
        ],
        1800,
    ),
    (["五星", "五星级", "豪华", "度假酒店", "度假"], 1300),
    (["高端酒店", "高端"], 1000),
    (["精品酒店", "中高端", "四星", "四星级"], 600),
]
LOW_END_HOTEL_FALLBACK_BLOCKLIST = [
    "经济",
    "快捷",
    "青年",
    "旅舍",
    "如家",
    "汉庭",
    "7天",
    "七天",
    "锦江之星",
    "格林豪泰",
    "速8",
    "布丁",
    "城市便捷",
]

FREE_ATTRACTION_KEYWORDS = ["广场", "步行街", "商业街", "外滩", "海滩", "沙滩", "街区", "夜市", "公园"]
LOW_TICKET_TYPE_KEYWORDS = ["公园", "寺庙", "园林", "纪念馆"]
MEDIUM_TICKET_TYPE_KEYWORDS = ["风景名胜", "动物园", "植物园", "科技馆", "文化场所"]
HIGH_TICKET_TYPE_KEYWORDS = ["主题公园", "游乐园", "海洋馆", "度假区", "演艺"]
PREMIUM_TICKET_KEYWORDS = [
    "迪士尼",
    "环球影城",
    "长隆",
    "主题公园",
    "游乐园",
    "海洋馆",
    "海洋公园",
    "旅游度假区",
    "滑雪",
]
PAID_EXPERIENCE_TICKET_KEYWORDS = [
    "演出",
    "实景演出",
    "剧场",
    "剧院",
    "游船",
    "夜游",
    "温泉",
    "索道",
    "缆车",
    "漂流",
]
MUSEUM_TYPE_KEYWORDS = ["博物馆", "博物院", "美术馆", "展览馆"]

MEAL_FALLBACK_PER_PERSON = {"breakfast": 25, "lunch": 60, "dinner": 90}
HIGH_END_MEAL_FALLBACK_RULES = [
    (["米其林", "omakase", "Omakase", "法餐"], 450),
    (["黑珍珠", "高端餐厅", "高端", "商务宴请"], 320),
    (["私房菜", "商务餐厅"], 260),
    (["精致餐厅", "品质餐厅", "创意菜"], 180),
]
HIGH_END_MEAL_BUCKET_FALLBACK = {
    "comfortable": 180,
    "premium": 260,
    "luxury": 380,
}

DEFAULT_ATTRACTION_PRICE_TABLE_PATH = Path(__file__).with_name("attraction_price_table.json")
ATTRACTION_PRICE_TABLE_PATH = Path(
    os.getenv("PLANNER_ATTRACTION_PRICE_TABLE_PATH", str(DEFAULT_ATTRACTION_PRICE_TABLE_PATH))
)


def with_hotel_cost_hints(rows: List[Dict[str, Any]], request: TripRequest) -> List[Dict[str, Any]]:
    """给酒店候选补稳定单晚价格 hint。"""
    results = []
    for row in rows:
        item = dict(row)
        amap_cost = parse_float(item.get("cost"))
        if amap_cost is not None and amap_cost > 0:
            item["estimated_cost_hint"] = round_to_50(amap_cost)
            item["cost_source"] = "amap_cost"
        else:
            item["estimated_cost_hint"], item["cost_source"] = estimate_hotel_cost_profile(request, item)
        results.append(item)
    return results


def with_ticket_price_hints(rows: List[Dict[str, Any]], request: TripRequest) -> List[Dict[str, Any]]:
    """给景点/体验候选补成人单人票价 hint。"""
    season = ticket_price_season(request)
    results = []
    for row in rows:
        item = dict(row)
        rule_price = estimate_ticket_price(item)
        amap_cost = parse_float(item.get("cost"))
        table_match = find_attraction_price_profile(request, item)

        if amap_cost is not None and amap_cost >= 0:
            item["ticket_price_hint"] = int(round(amap_cost or 0))
            item["ticket_price_source"] = "amap_cost"
        elif table_match is not None:
            item["ticket_price_hint"] = table_price_for_season(table_match, season)
            item["ticket_price_source"] = table_match.get("ticket_price_source") or "price_table"
            item["ticket_price_table_name"] = table_match.get("name", "")
            item["ticket_price_confidence"] = table_match.get("confidence", "")
        else:
            item["ticket_price_hint"] = rule_price
            item["ticket_price_source"] = "rule_estimated"
        item["ticket_price_season"] = season
        results.append(item)
    return results


def with_meal_cost_hints(rows: List[Dict[str, Any]], request: TripRequest) -> List[Dict[str, Any]]:
    """给餐饮候选补单人单餐价格 hint。"""
    results = []
    for row in rows:
        item = dict(row)
        amap_cost = parse_float(item.get("cost"))
        if amap_cost is not None and amap_cost > 0:
            item["cost_unit"] = "per_person"
            item["meal_cost_hint"] = int(round(amap_cost))
            item["cost_source"] = "amap_cost"
            item["price_level"] = meal_price_level(amap_cost)
        else:
            item["cost_unit"] = "per_person"
            item["meal_cost_hint"], item["cost_source"] = fallback_meal_cost_profile(item, request)
            item["price_level"] = meal_price_level(item["meal_cost_hint"])
        results.append(item)
    return results


def fallback_meal_cost(row: Dict[str, Any], request: TripRequest) -> int:
    """没有人均价时按餐别给稳定 fallback。"""
    return fallback_meal_cost_profile(row, request)[0]


def fallback_meal_cost_profile(row: Dict[str, Any], request: TripRequest) -> tuple[int, str]:
    """Return fallback meal cost and whether it is high-end estimated."""
    roles = {str(role or "").strip().lower() for role in row.get("meal_roles") or []}
    if roles == {"breakfast"} or str(row.get("source_bucket") or "") == "food_breakfast":
        return MEAL_FALLBACK_PER_PERSON["breakfast"], "rule_estimated"
    text = meal_price_text(row)
    for keywords, value in HIGH_END_MEAL_FALLBACK_RULES:
        if any(keyword in text for keyword in keywords):
            return value, "rule_estimated_high_end"
    if str(row.get("source_bucket") or "") in {"food_budget_upgrade", "food_budget"}:
        budget_level = request.budget_constraint.budget_level or ""
        if budget_level in HIGH_END_MEAL_BUCKET_FALLBACK:
            return HIGH_END_MEAL_BUCKET_FALLBACK[budget_level], "rule_estimated_high_end"
    return MEAL_FALLBACK_PER_PERSON["lunch"], "rule_estimated"


def meal_price_text(row: Dict[str, Any]) -> str:
    """拼出用于餐饮价格兜底判断的文本。"""
    values = [
        row.get("name"),
        row.get("type"),
        row.get("address"),
        row.get("source_keyword"),
        row.get("source_bucket"),
        " ".join(str(tag) for tag in row.get("cuisine_tags") or []),
    ]
    return ";".join(str(value or "") for value in values)


def meal_price_level(per_person_cost: float) -> str:
    """按人均餐饮价格给 Planner 一个粗预算档位。"""
    if per_person_cost <= 40:
        return "budget"
    if per_person_cost <= 100:
        return "standard"
    if per_person_cost <= 180:
        return "premium"
    return "luxury"


def estimate_hotel_cost(request: TripRequest, row: Dict[str, Any]) -> int:
    """按住宿偏好、POI名称和城市层级估算单晚价格。"""
    text = f"{request.accommodation};{row.get('name') or ''};{row.get('type') or ''}"
    base = 220
    for keywords, value in HOTEL_BASE_COST_BY_TYPE:
        if any(keyword in text for keyword in keywords):
            base = value
            break
    factor = HOTEL_CITY_FACTORS.get(request.city, 1.0)
    return cap_hotel_fallback_cost(request, round_to_50(base * factor))


def estimate_hotel_cost_profile(request: TripRequest, row: Dict[str, Any]) -> tuple[int, str]:
    """Return fallback hotel price and whether it is a high-end estimate."""
    high_end_cost = estimate_high_end_hotel_cost(request, row)
    if high_end_cost is not None:
        return high_end_cost, "rule_estimated_high_end"
    return estimate_hotel_cost(request, row), "rule_estimated"


def estimate_high_end_hotel_cost(request: TripRequest, row: Dict[str, Any]) -> Optional[int]:
    """Estimate missing prices only when the row itself has strong high-end signals."""
    text = high_end_hotel_price_text(row)
    if any(keyword in low_end_hotel_block_text(row) for keyword in LOW_END_HOTEL_FALLBACK_BLOCKLIST):
        return None
    base = None
    for keywords, value in HIGH_END_HOTEL_FALLBACK_BY_SIGNAL:
        if any(keyword in text for keyword in keywords):
            base = value
            break
    if base is None:
        return None
    factor = HOTEL_CITY_FACTORS.get(request.city, 1.0)
    return cap_hotel_fallback_cost(request, round_to_50(base * factor))


def cap_hotel_fallback_cost(request: TripRequest, cost: int) -> int:
    """Cap rule-estimated hotel prices for mid-budget requests."""
    budget_level = ""
    if request.budget_constraint:
        budget_level = request.budget_constraint.budget_level or ""
    cap = HOTEL_FALLBACK_CAP_BY_BUDGET_LEVEL.get(budget_level)
    if cap is not None and cost > cap:
        return cap
    return cost


def high_end_hotel_price_text(row: Dict[str, Any]) -> str:
    """Text used for high-end hotel fallback; excludes request accommodation."""
    values = [
        row.get("name"),
        row.get("type"),
        row.get("address"),
    ]
    if row.get("local_table") == "high_end_poi_table":
        values.extend([row.get("source_keyword"), row.get("source_bucket")])
    return ";".join(str(value or "") for value in values)


def low_end_hotel_block_text(row: Dict[str, Any]) -> str:
    """Text used to block obvious economy chains without matching street names."""
    values = [row.get("name"), row.get("type"), row.get("source_keyword")]
    return ";".join(str(value or "") for value in values)


def estimate_ticket_price(row: Dict[str, Any]) -> int:
    """规则估算成人单人门票。"""
    name = str(row.get("name") or "")
    poi_type = str(row.get("type") or "")
    source_keyword = str(row.get("source_keyword") or "")
    source_bucket = str(row.get("source_bucket") or "")
    text = f"{name};{poi_type};{source_keyword};{source_bucket}"

    if any(keyword in text for keyword in PREMIUM_TICKET_KEYWORDS):
        return 280
    if any(keyword in text for keyword in PAID_EXPERIENCE_TICKET_KEYWORDS):
        return 180
    if any(keyword in text for keyword in FREE_ATTRACTION_KEYWORDS):
        return 0
    if any(keyword in text for keyword in HIGH_TICKET_TYPE_KEYWORDS):
        return 180
    if any(keyword in text for keyword in MEDIUM_TICKET_TYPE_KEYWORDS):
        return 80
    if any(keyword in text for keyword in LOW_TICKET_TYPE_KEYWORDS):
        return 30
    if any(keyword in text for keyword in MUSEUM_TYPE_KEYWORDS):
        return 0
    return 60


def find_attraction_price_profile(request: TripRequest, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """从本地热门景点票价画像表查找匹配项。"""
    table = load_attraction_price_table()
    if not table:
        return None

    row_city = normalize_city(row.get("cityname") or request.city)
    request_city = normalize_city(request.city)
    row_aliases = poi_name_aliases(str(row.get("name") or ""))
    if not row_aliases:
        return None

    best_match = None
    best_score = -1
    for item in table:
        item_city = normalize_city(item.get("city") or "")
        if item_city and item_city not in {request_city, row_city}:
            continue

        item_aliases = []
        for name in [item.get("name", "")] + list(item.get("aliases") or []):
            item_aliases.extend(poi_name_aliases(str(name)))

        score = price_profile_match_score(row_aliases, item_aliases)
        if score > best_score:
            best_score = score
            best_match = item

    return best_match if best_score > 0 else None


def price_profile_match_score(row_aliases: List[str], item_aliases: List[str]) -> int:
    """票价表名称匹配分数，优先精确匹配，其次弱包含。"""
    score = 0
    for left in row_aliases:
        for right in item_aliases:
            if not left or not right:
                continue
            if left == right:
                score = max(score, 100 + len(left))
            elif len(left) >= 2 and len(right) >= 2 and (left in right or right in left):
                score = max(score, 50 + min(len(left), len(right)))
    return score


def table_price_for_season(item: Dict[str, Any], season: str) -> int:
    """按季节从票价画像里取价，缺季节时回退平季。"""
    profile = item.get("ticket_price_profile") or {}
    value = profile.get(season)
    if value is None:
        value = profile.get("normal_season")
    if value is None:
        value = profile.get("peak_season")
    if value is None:
        value = profile.get("off_season", 0)
    return int(round(parse_float(value) or 0))


@lru_cache(maxsize=1)
def load_attraction_price_table() -> List[Dict[str, Any]]:
    """加载本地热门景点票价画像表。"""
    path = ATTRACTION_PRICE_TABLE_PATH
    if not path.is_absolute():
        path = DEFAULT_ATTRACTION_PRICE_TABLE_PATH.parent / path
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except Exception as exc:
        print(f"⚠️  景点票价表读取失败: {path} | {exc}")
        return []
    return list(data.get("items") or [])


def normalize_city(value: Any) -> str:
    """城市名归一化，兼容“北京市”和“北京”。"""
    text = str(value or "").strip()
    return re.sub(r"(市|地区|特别行政区)$", "", text)


def normalize_poi_name(value: Any) -> str:
    """景点名归一化，用于票价表匹配。"""
    return normalize_planner_poi_name(str(value or ""))


def poi_name_aliases(name: str) -> List[str]:
    """生成少量别名，兼容“锦里古街”vs“锦里”这类匹配。"""
    base = normalize_poi_name(name)
    if not base:
        return []

    aliases = {base}
    for suffix in ["风景名胜区", "风景区", "旅游区", "景区", "公园", "古街", "博物馆", "博物院", "度假区"]:
        if base.endswith(suffix) and len(base) > len(suffix) + 1:
            aliases.add(base[: -len(suffix)])

    return sorted(alias for alias in aliases if len(alias) >= 2)


def ticket_price_season(request: TripRequest) -> str:
    """按出行月份粗分票价季节，第一版不做节假日精细化。"""
    month = datetime.strptime(request.start_date, "%Y-%m-%d").month
    if month in {11, 12, 1, 2, 3}:
        return "off_season"
    if month in {7, 8}:
        return "peak_season"
    return "normal_season"


def round_to_50(value: float) -> int:
    """价格 hint 统一按 50 元档位取整，避免伪精确。"""
    return int(round(value / 50.0) * 50)


def parse_float(value: Any) -> Optional[float]:
    """解析高德biz_ext里的评分/价格。"""
    if value in (None, "", []):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
