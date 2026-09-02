"""Planner 输出解析、校验和兜底计划。"""

import json
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..models.schemas import TripRequest, TripPlan, DayPlan, Attraction, Meal, WeatherInfo, Location
from .dates import trip_date_strings, unknown_weather_row


POI_NAME_SUFFIXES = [
    "历史文化街区",
    "风景名胜区",
    "旅游景区",
    "森林公园",
    "湿地公园",
    "研究基地",
    "步行街",
    "文化街区",
    "商业街区",
    "博物馆",
    "博物院",
    "纪念馆",
    "美术馆",
    "艺术馆",
    "科技馆",
    "展览馆",
    "风景区",
    "旅游区",
    "古街区",
    "景区",
    "公园",
    "古街",
    "老街",
    "古镇",
    "基地",
    "中心",
    "广场",
]

POI_CITY_PREFIXES = [
    "北京",
    "上海",
    "广州",
    "深圳",
    "杭州",
    "成都",
    "重庆",
    "西安",
    "南京",
    "苏州",
    "厦门",
    "青岛",
    "武汉",
    "长沙",
    "昆明",
    "大理",
    "丽江",
    "桂林",
    "三亚",
    "哈尔滨",
]

TRADITIONAL_POI_CHAR_MAP = str.maketrans(
    {
        "發": "发",
        "髮": "发",
        "隨": "随",
        "園": "园",
        "館": "馆",
        "舘": "馆",
        "樓": "楼",
        "廳": "厅",
        "廚": "厨",
        "齋": "斋",
        "寶": "宝",
        "貝": "贝",
        "龍": "龙",
        "鳳": "凤",
        "麗": "丽",
        "樂": "乐",
        "麥": "麦",
        "麵": "面",
        "魚": "鱼",
        "鮮": "鲜",
        "雞": "鸡",
        "鴨": "鸭",
        "鵝": "鹅",
        "滷": "卤",
        "鹵": "卤",
        "燒": "烧",
        "鍋": "锅",
        "湯": "汤",
        "粵": "粤",
        "廣": "广",
        "東": "东",
        "雲": "云",
        "臺": "台",
        "灣": "湾",
        "門": "门",
        "閣": "阁",
        "舊": "旧",
        "藝": "艺",
        "鄉": "乡",
        "鎮": "镇",
        "縣": "县",
        "區": "区",
        "國": "国",
        "華": "华",
        "順": "顺",
        "親": "亲",
        "實": "实",
        "師": "师",
        "壹": "一",
        "貳": "二",
        "參": "三",
        "叁": "三",
        "萬": "万",
        "點": "点",
        "號": "号",
        "會": "会",
        "軒": "轩",
        "莊": "庄",
        "餅": "饼",
        "餃": "饺",
        "飯": "饭",
        "飲": "饮",
        "餛": "馄",
        "飩": "饨",
        "鱔": "鳝",
        "蝦": "虾",
        "醬": "酱",
        "醃": "腌",
        "臘": "腊",
        "衚": "胡",
        "鬍": "胡",
        "裏": "里",
        "裡": "里",
        "內": "内",
        "長": "长",
        "慶": "庆",
        "賓": "宾",
        "貴": "贵",
        "陽": "阳",
        "寧": "宁",
        "蘇": "苏",
        "廈": "厦",
        "錦": "锦",
        "橋": "桥",
        "頭": "头",
        "島": "岛",
        "濱": "滨",
        "獅": "狮",
        "龜": "龟",
        "鷺": "鹭",
        "遙": "遥",
        "遊": "游",
        "覽": "览",
        "戲": "戏",
        "劇": "剧",
        "場": "场",
        "舖": "铺",
        "鋪": "铺",
        "車": "车",
        "馬": "马",
        "騰": "腾",
        "騎": "骑",
        "範": "范",
        "豐": "丰",
        "億": "亿",
        "銀": "银",
        "鐵": "铁",
        "鉑": "铂",
        "鑽": "钻",
    }
)

POI_BRACKET_CONTENT_RE = re.compile(r"[\(\[\{<【（［｛].*?[\)\]\}>】）］｝]")
POI_KEEP_ALNUM_CJK_RE = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")

INVALID_HOTEL_NAME_MARKERS = [
    "无住宿",
    "无需住宿",
    "不用住宿",
    "不住宿",
    "无酒店",
    "不用酒店",
    "返程",
    "回程",
    "离店",
]

INVALID_HOTEL_NAMES = {"无", "无住宿", "无需住宿", "不住宿", "无酒店", "返程", "当天返程", "回程"}

PLACEHOLDER_MEAL_NAMES = {
    "早餐",
    "午餐",
    "晚餐",
    "早餐推荐",
    "午餐推荐",
    "晚餐推荐",
    "餐饮推荐",
    "本地早餐",
    "本地午餐",
    "本地晚餐",
    "当地早餐",
    "当地午餐",
    "当地晚餐",
    "特色早餐",
    "特色午餐",
    "特色晚餐",
    "特色餐厅",
}

HOTEL_BREAKFAST_MARKERS = ["酒店早餐", "酒店自助早餐", "民宿早餐", "客栈早餐", "住宿早餐"]

HOTEL_DISTANCE_PLACEHOLDER_NAMES = {
    "距离景点2公里",
    "距景点2公里",
    "距离主要景点2公里",
    "距主要景点2公里",
    "距离当日景点2公里",
    "距当日景点2公里",
}


def extract_json_object(response: str) -> Dict[str, Any]:
    """Extract a top-level JSON object from an LLM response.

    这里不要从任意内层 `{` 开始扫描。顶层 JSON 被截断时，内层
    day/hotel/attraction 对象可能仍然是合法 JSON，但它不是 TripPlan。
    """
    decoder = json.JSONDecoder()
    candidates = []

    if "```json" in response:
        json_start = response.find("```json") + 7
        json_end = response.find("```", json_start)
        if json_end != -1:
            candidates.append(response[json_start:json_end].strip())

    if "```" in response:
        json_start = response.find("```") + 3
        json_end = response.find("```", json_start)
        if json_end != -1:
            candidates.append(response[json_start:json_end].strip())

    candidates.append(response.strip())

    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate.startswith("{"):
            continue
        try:
            data, end_index = decoder.raw_decode(candidate)
        except json.JSONDecodeError:
            continue
        trailing_text = candidate[end_index:].strip()
        if trailing_text:
            continue
        if isinstance(data, dict):
            required_keys = {"city", "start_date", "end_date", "days", "overall_suggestions"}
            if required_keys.issubset(data.keys()):
                return data

    raise ValueError("响应中未找到完整的顶层TripPlan JSON对象")


def validate_trip_plan_shape(
    trip_plan: TripPlan,
    request: TripRequest,
    planner_context: Optional[Dict[str, Any]] = None,
) -> None:
    """Validate high-level shape beyond Pydantic field types."""
    if trip_plan.city != request.city:
        raise ValueError(f"city不匹配: expected={request.city}, got={trip_plan.city}")
    if trip_plan.start_date != request.start_date or trip_plan.end_date != request.end_date:
        raise ValueError("start_date/end_date与请求不匹配")
    if len(trip_plan.days) != request.travel_days:
        raise ValueError(f"days长度不匹配: expected={request.travel_days}, got={len(trip_plan.days)}")

    expected_dates = trip_date_strings(request)
    for index, day in enumerate(trip_plan.days):
        if day.day_index != index:
            raise ValueError(f"第{index + 1}天day_index不匹配: expected={index}, got={day.day_index}")
        if day.date != expected_dates[index]:
            raise ValueError(f"第{index + 1}天date不匹配: expected={expected_dates[index]}, got={day.date}")
        if day.hotel and is_invalid_hotel_name(day.hotel.name):
            raise ValueError(f"第{index + 1}天hotel.name不能是无住宿/返程占位: {day.hotel.name}")
        if day.hotel and is_placeholder_hotel_distance(day.hotel.distance):
            raise ValueError(f"第{index + 1}天hotel.distance不能是伪精确距离占位: {day.hotel.distance}")
        if not day.attractions:
            raise ValueError(f"第{index + 1}天缺少attractions")
        if len(day.meals) < 3:
            raise ValueError(f"第{index + 1}天meals少于3项")
        for meal in day.meals:
            if is_placeholder_meal_name(meal.name):
                raise ValueError(f"第{index + 1}天meal.name不能是餐饮占位词: {meal.name}")

    weather_dates = [item.date for item in trip_plan.weather_info]
    if weather_dates != expected_dates:
        raise ValueError(f"weather_info日期不匹配: expected={expected_dates}, got={weather_dates}")

    if planner_context:
        warn_plan_grounding(trip_plan, planner_context)


def warn_plan_grounding(trip_plan: TripPlan, planner_context: Dict[str, Any]) -> None:
    """对POI是否来自工具候选做软检查；先不硬拦，避免高德召回缺口导致线上不可用。"""
    snapshot = planner_context.get("tool_snapshot", {})
    scenic_names = candidate_names(
        (snapshot.get("classic_pois") or [])
        + (snapshot.get("preference_pois") or [])
        + (snapshot.get("scenic_pois") or [])
        + (snapshot.get("experience_pois") or [])
    )
    hotel_names = candidate_names(snapshot.get("hotel_pois") or [])
    food_names = candidate_names(snapshot.get("food_pois") or [])

    ungrounded_attractions = []
    for day in trip_plan.days:
        for attraction in day.attractions:
            if scenic_names and not name_in_candidates(attraction.name, scenic_names):
                ungrounded_attractions.append(attraction.name)

    ungrounded_hotels = []
    for day in trip_plan.days:
        if day.hotel and hotel_names and not name_in_candidates(day.hotel.name, hotel_names):
            ungrounded_hotels.append(day.hotel.name)

    if ungrounded_attractions:
        preview = ", ".join(ungrounded_attractions[:5])
        print(f"⚠️  Planner输出中有未命中工具候选的景点: {preview}")
    if ungrounded_hotels:
        preview = ", ".join(ungrounded_hotels[:3])
        print(f"⚠️  Planner输出中有未命中工具候选的酒店: {preview}")

    ungrounded_meals = []
    for day in trip_plan.days:
        for meal in day.meals:
            if is_lodging_breakfast_meal(meal.name, meal.type):
                continue
            if food_names and not name_in_candidates(meal.name, food_names):
                ungrounded_meals.append(meal.name)

    if ungrounded_meals:
        preview = ", ".join(ungrounded_meals[:5])
        print(f"⚠️  Planner输出中有未命中餐饮候选的餐饮: {preview}")


def enrich_trip_plan_poi_details(trip_plan: TripPlan, planner_context: Dict[str, Any]) -> None:
    """用工具候选回填模型容易漏掉的 POI 地址和坐标。

    Planner 有时只复制了餐厅名和价格，没有把 food_pois 中的 address/location
    带进最终 JSON。前端地图依赖坐标，这里在返回前做确定性回填。
    """
    snapshot = planner_context.get("tool_snapshot", {})
    food_pois = snapshot.get("food_pois") or []
    if not food_pois:
        return

    filled_meal_locations = 0
    filled_meal_addresses = 0

    for day in trip_plan.days:
        for meal in day.meals:
            if is_lodging_breakfast_meal(meal.name, meal.type):
                continue

            candidate = find_candidate_by_name(meal.name, food_pois)
            if not candidate:
                continue

            if not meal.address and candidate.get("address"):
                meal.address = str(candidate.get("address") or "")
                filled_meal_addresses += 1

            if meal.location is None:
                location = location_from_candidate(candidate)
                if location:
                    meal.location = location
                    filled_meal_locations += 1

    if filled_meal_locations or filled_meal_addresses:
        print(
            "✅ 已回填餐饮POI信息: "
            f"坐标={filled_meal_locations}, 地址={filled_meal_addresses}"
        )


def find_candidate_by_name(name: str, candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """按归一化别名从候选列表中找回最接近的 POI。"""
    name_aliases = poi_name_aliases(name)
    if not name_aliases:
        return None

    for candidate in candidates:
        candidate_aliases = poi_name_aliases(str(candidate.get("name") or ""))
        if any(left == right for left in name_aliases for right in candidate_aliases):
            return candidate

    for candidate in candidates:
        candidate_aliases = poi_name_aliases(str(candidate.get("name") or ""))
        if any(left in right or right in left for left in name_aliases for right in candidate_aliases):
            return candidate

    return None


def location_from_candidate(candidate: Dict[str, Any]) -> Optional[Location]:
    """安全地把候选 POI location 转成响应 schema 的 Location。"""
    location = candidate.get("location") or {}
    try:
        longitude = float(location.get("longitude"))
        latitude = float(location.get("latitude"))
    except (TypeError, ValueError, AttributeError):
        return None

    return Location(longitude=longitude, latitude=latitude)


def candidate_names(rows: List[Dict[str, Any]]) -> List[str]:
    """抽取候选名称。"""
    return [row.get("name", "") for row in rows if row.get("name")]


def name_in_candidates(name: str, candidates: List[str]) -> bool:
    """宽松名称匹配，兼容“锦里古街”vs“锦里”这类别名。"""
    name_aliases = poi_name_aliases(name)
    if not name_aliases:
        return False

    for candidate in candidates:
        candidate_aliases = poi_name_aliases(candidate)
        for left in name_aliases:
            for right in candidate_aliases:
                if left == right or left in right or right in left:
                    return True
    return False


def normalize_poi_name(name: str) -> str:
    """用于日志告警的POI名称归一化，不改变模型最终输出。"""
    text = unicodedata.normalize("NFKC", str(name or "")).strip().lower()
    text = POI_BRACKET_CONTENT_RE.sub("", text)
    text = text.translate(TRADITIONAL_POI_CHAR_MAP)
    text = text.replace("&", "and")
    text = POI_KEEP_ALNUM_CJK_RE.sub("", text)
    return text


def poi_name_aliases(name: str) -> List[str]:
    """生成少量可解释别名，减少工具候选命中日志里的假阳性。"""
    base = normalize_poi_name(name)
    if not base:
        return []

    aliases = {base}

    for prefix in POI_CITY_PREFIXES:
        if base.startswith(prefix) and len(base) > len(prefix) + 1:
            aliases.add(base[len(prefix):])

    for alias in list(aliases):
        for suffix in POI_NAME_SUFFIXES:
            if alias.endswith(suffix) and len(alias) > len(suffix) + 1:
                aliases.add(alias[: -len(suffix)])

    return sorted(alias for alias in aliases if len(alias) >= 2)


def is_invalid_hotel_name(name: str) -> bool:
    """识别模型把“无住宿/返程”写进 hotel.name 的脏数据。"""
    normalized = normalize_poi_name(name)
    if not normalized:
        return True
    if normalized in {normalize_poi_name(item) for item in INVALID_HOTEL_NAMES}:
        return True
    return any(marker in normalized for marker in INVALID_HOTEL_NAME_MARKERS)


def is_placeholder_hotel_distance(distance: str) -> bool:
    """识别模型编出来的酒店距离占位。

    当前没有真实路线/距离工具，宁愿 distance 为空，也不要让“距离景点2公里”
    这类看似精确的假字段进入前端和训练数据。
    """
    text = str(distance or "").strip()
    if not text:
        return False
    normalized = normalize_poi_name(text)
    placeholder_names = {normalize_poi_name(item) for item in HOTEL_DISTANCE_PLACEHOLDER_NAMES}
    if normalized in placeholder_names:
        return True
    return bool(re.fullmatch(r"(距离|距)(当日|主要|周边|附近)?景点约?\d+(公里|km|米|m)", normalized))


def is_placeholder_meal_name(name: str) -> bool:
    """识别模型输出的餐饮占位词。

    这类名字满足 schema，但没有真实餐饮内容，会污染线上体验和评估。
    """
    normalized = normalize_poi_name(name)
    if not normalized:
        return True
    placeholder_names = {normalize_poi_name(item) for item in PLACEHOLDER_MEAL_NAMES}
    if normalized in placeholder_names:
        return True
    if re.fullmatch(r"第?\d+天?(早餐|午餐|晚餐)", normalized):
        return True
    return False


def is_hotel_breakfast_name(name: str) -> bool:
    """酒店/民宿早餐不是 food_pois，但可以作为早餐来源。"""
    normalized = normalize_poi_name(name)
    return any(normalize_poi_name(marker) in normalized for marker in HOTEL_BREAKFAST_MARKERS)


def is_lodging_breakfast_meal(name: str, meal_type: str) -> bool:
    """只有早餐餐次可以把住宿早餐视为已 grounding。"""
    return str(meal_type or "").strip().lower() == "breakfast" and is_hotel_breakfast_name(name)


def create_fallback_plan(request: TripRequest) -> TripPlan:
    """创建备用计划(当Agent失败时)。"""
    start_date = datetime.strptime(request.start_date, "%Y-%m-%d")

    days = []
    for i in range(request.travel_days):
        current_date = start_date + timedelta(days=i)

        day_plan = DayPlan(
            date=current_date.strftime("%Y-%m-%d"),
            day_index=i,
            description=f"第{i+1}天行程",
            transportation=request.transportation,
            accommodation=request.accommodation,
            attractions=[
                Attraction(
                    name=f"{request.city}景点{j+1}",
                    address=f"{request.city}市",
                    location=Location(longitude=116.4 + i*0.01 + j*0.005, latitude=39.9 + i*0.01 + j*0.005),
                    visit_duration=120,
                    description=f"这是{request.city}的著名景点",
                    category="景点"
                )
                for j in range(2)
            ],
            meals=[
                Meal(type="breakfast", name="酒店早餐", description="根据住宿条件安排早餐"),
                Meal(type="lunch", name=f"{request.city}本地菜午餐", description="按用户口味选择当地餐厅"),
                Meal(type="dinner", name=f"{request.city}特色晚餐", description="按用户口味选择当地餐厅")
            ]
        )
        days.append(day_plan)

    return TripPlan(
        city=request.city,
        start_date=request.start_date,
        end_date=request.end_date,
        days=days,
        weather_info=[
            WeatherInfo(**unknown_weather_row(date_text))
            for date_text in trip_date_strings(request)
        ],
        overall_suggestions=f"这是为您规划的{request.city}{request.travel_days}日游行程,建议提前查看各景点的开放时间和临近天气。"
    )
