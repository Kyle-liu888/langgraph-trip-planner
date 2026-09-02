"""Planner POI 关键词、规范化、过滤和排序逻辑。"""

from typing import Any, Dict, List, Optional

from ..models.schemas import TripRequest


CLASSIC_SCENIC_KEYWORDS = [
    "必游景点",
    "著名景点",
    "热门景点",
    "博物馆",
    "历史文化",
    "公园",
]

POI_NOISE_KEYWORDS = [
    "培训",
    "留学",
    "考研",
    "四六级",
    "教育",
    "学校",
    "公司",
    "产业园",
    "批发",
    "市场",
    "建材",
    "房产",
    "维修",
    "物流",
]
EXPERIENCE_ALLOWED_TYPE_KEYWORDS = [
    "风景名胜",
    "博物馆",
    "美术馆",
    "展览馆",
    "科技馆",
    "文化场所",
    "剧场",
    "影剧院",
    "休闲场所",
    "娱乐场所",
    "体育休闲",
]
SCENIC_ALLOWED_TYPE_KEYWORDS = [
    "风景名胜",
    "博物馆",
    "美术馆",
    "展览馆",
    "科技馆",
    "公园",
    "广场",
    "特色商业街",
    "商业街",
    "纪念馆",
    "寺庙",
    "文化场所",
]
ATTRACTION_BUDGET_UPGRADE_KEYWORDS = {
    "comfortable": ["主题公园", "海洋馆", "游船", "夜游", "温泉景区"],
    "premium": ["主题公园", "海洋馆", "旅游度假区", "大型景区", "索道", "游船", "夜游"],
    "luxury": ["主题公园", "旅游度假区", "高端景区", "索道", "游船", "夜游", "滑雪场"],
}
ATTRACTION_PREFERENCE_KEYWORD_MAP = {
    "美食": ["美食街", "小吃街", "特色商业街"],
    "本地美食": ["美食街", "小吃街", "老街"],
    "本地菜": ["老街", "美食街"],
    "特色餐厅": ["美食街", "特色商业街"],
    "老字号": ["老街", "历史街区", "非遗街区"],
    "夜市": ["夜市", "夜市街区", "步行街"],
    "夜市夜景": ["夜市", "夜景街区", "步行街"],
    "城市漫步": ["步行街", "历史街区", "老街", "滨江步道"],
    "购物": ["步行街", "商业街", "特色商业街"],
    "购物商圈": ["步行街", "商业街", "特色商业街"],
}
FOOD_AVOID_KEYWORDS = ["海鲜", "牛肉", "羊肉", "猪肉", "辣", "酒", "生冷"]
FOOD_AVOID_MARKERS = ["过敏", "不吃", "不要", "避免", "忌", "禁忌", "不能吃", "不想吃", "别吃"]
DIET_PREFERENCE_KEYWORDS = ["素食", "清真", "少辣", "本地菜", "海鲜"]
FOOD_BREAKFAST_KEYWORDS = ["早餐", "早点", "早茶", "包子", "粥", "面馆", "糕点", "咖啡"]
FOOD_BASE_KEYWORDS = ["本地菜", "特色餐厅", "老字号", "小吃", "早餐", "简餐"]
FOOD_COMPANION_KEYWORDS = {
    "family_with_children": ["亲子餐厅", "家常菜"],
    "family_with_elders": ["家常菜", "清淡餐厅"],
    "business": ["商务餐厅", "商务宴请", "高端餐厅"],
}
FOOD_BUDGET_KEYWORDS = {
    "limited": ["小吃", "快餐", "简餐"],
    "standard": ["本地菜", "特色餐厅", "老字号"],
    "comfortable": ["精致餐厅", "创意菜", "品质餐厅"],
    "premium": ["高端餐厅", "精致餐厅", "黑珍珠餐厅", "商务餐厅", "品质餐厅"],
    "luxury": ["黑珍珠餐厅", "米其林餐厅", "高端餐厅", "omakase", "法餐"],
}
FOOD_BUDGET_UPGRADE_KEYWORDS = {
    "comfortable": ["精致餐厅", "创意菜", "品质餐厅", "高端餐厅", "私房菜", "融合菜", "商务餐厅"],
    "premium": [
        "高端餐厅",
        "精致餐厅",
        "黑珍珠餐厅",
        "创意菜",
        "私房菜",
        "商务宴请",
        "商务餐厅",
        "品质餐厅",
        "融合菜",
        "高档餐厅",
        "酒店餐厅",
        "宴请餐厅",
    ],
    "luxury": [
        "黑珍珠餐厅",
        "米其林餐厅",
        "高端餐厅",
        "私房菜",
        "omakase",
        "法餐",
        "商务宴请",
        "酒店餐厅",
        "融合菜",
    ],
}
FOOD_BUDGET_SUPPLEMENT_KEYWORDS = {
    "comfortable": ["品质餐厅", "商务餐厅", "融合菜", "私房菜", "酒楼", "中餐厅", "酒店中餐厅"],
    "premium": [
        "商务餐厅",
        "品质餐厅",
        "融合菜",
        "私房菜",
        "酒楼",
        "中餐厅",
        "酒店中餐厅",
        "海鲜餐厅",
        "日料",
        "牛排",
        "西餐厅",
        "火锅",
    ],
    "luxury": [
        "黑珍珠餐厅",
        "米其林餐厅",
        "高端餐厅",
        "酒店中餐厅",
        "海鲜餐厅",
        "日料",
        "牛排",
        "西餐厅",
        "法餐",
        "omakase",
    ],
}
HOTEL_BUDGET_UPGRADE_KEYWORDS = {
    "premium": ["高端酒店", "五星级酒店", "豪华酒店", "度假酒店"],
    "luxury": ["奢华酒店", "五星级酒店", "豪华酒店", "度假酒店"],
}
EXPERIENCE_BUDGET_UPGRADE_KEYWORDS = {
    "comfortable": ["演出", "游船", "夜游", "温泉", "剧场"],
    "premium": ["主题公园", "演出", "实景演出", "沉浸式剧场", "游船", "夜游", "温泉", "滑雪场"],
    "luxury": ["高端体验", "实景演出", "沉浸式剧场", "游船", "夜游", "温泉度假村", "滑雪场"],
}
FOOD_PREFERENCE_KEYWORD_MAP = {
    "美食": ["本地菜", "特色餐厅", "小吃"],
    "本地菜": ["本地菜", "老字号"],
    "特色餐厅": ["特色餐厅", "老字号"],
    "老字号": ["老字号"],
    "夜市": ["夜市", "小吃"],
    "咖啡": ["咖啡"],
    "购物": ["商场餐厅", "特色餐厅"],
    "亲子": ["亲子餐厅", "家常菜"],
    "老人友好": ["家常菜", "清淡餐厅"],
}
FOOD_TAG_KEYWORDS = [
    "本地菜",
    "特色餐厅",
    "老字号",
    "小吃",
    "早餐",
    "早点",
    "早茶",
    "包子",
    "粥",
    "面馆",
    "糕点",
    "简餐",
    "快餐",
    "咖啡",
    "夜市",
    "亲子餐厅",
    "家常菜",
    "清淡餐厅",
    "高端餐厅",
    "精致餐厅",
    "品质餐厅",
    "商务餐厅",
    "商务宴请",
    "黑珍珠",
    "米其林",
    "创意菜",
    "私房菜",
    "法餐",
    "omakase",
    "清真",
    "素食",
    "海鲜",
]
NEGATIVE_PREFERENCE_MARKERS = [
    "过敏",
    "不吃",
    "不要",
    "避免",
    "避开",
    "忌",
    "禁忌",
    "不能",
    "不想",
    "别",
    "少走路",
]


def build_poi_keywords(request: TripRequest, role: str) -> List[str]:
    """根据请求构造稳定的POI搜索关键词。"""
    preferences = positive_preference_tags(request)

    if role == "classic":
        return CLASSIC_SCENIC_KEYWORDS

    if role in {"scenic", "preference"}:
        keywords = build_attraction_preference_keywords(preferences)
        keywords.extend(["景点", "博物馆", "公园"])
        return unique_strings(keywords)[:6]

    if role == "experience":
        keywords = [f"{item}体验" for item in preferences[:2]]
        keywords.extend(["文化体验", "休闲娱乐"])
        return unique_strings(keywords)[:3]

    if role == "food":
        food_constraints = infer_food_constraints(request)
        diet = food_constraints["diet"]
        keywords = []
        if diet and diet != "无":
            keywords.append(diet)
        if any("美食" in item or "餐" in item for item in preferences):
            keywords.extend(preferences)
        keywords.extend(["特色餐厅", "本地菜"])
        return unique_strings(keywords)[:3]

    return ["景点"]


def build_budget_upgrade_keywords(request: TripRequest, role: str) -> List[str]:
    """预算较宽时额外补召回高价景点/体验/餐饮候选。"""
    budget_level = request.budget_constraint.budget_level or ""
    if role in {"scenic", "attraction", "preference"}:
        return ATTRACTION_BUDGET_UPGRADE_KEYWORDS.get(budget_level, [])
    if role == "experience":
        return EXPERIENCE_BUDGET_UPGRADE_KEYWORDS.get(budget_level, [])
    if role == "food":
        if avoids_expensive_food(request):
            return []
        return FOOD_BUDGET_UPGRADE_KEYWORDS.get(budget_level, [])
    return []


def build_food_budget_supplement_keywords(request: TripRequest) -> List[str]:
    """预算较高但午晚餐候选不足时，用更宽的正餐关键词补召回。"""
    if avoids_expensive_food(request):
        return []
    budget_level = request.budget_constraint.budget_level or ""
    return FOOD_BUDGET_SUPPLEMENT_KEYWORDS.get(budget_level, [])


def build_hotel_keyword_groups(request: TripRequest) -> List[Dict[str, Any]]:
    """构造酒店搜索分桶，预算较宽时给高价住宿候选保底。"""
    keyword = request.accommodation or "酒店"
    if "酒店" not in keyword and "宾馆" not in keyword and "民宿" not in keyword:
        keyword = f"{keyword}酒店"

    groups: List[Dict[str, Any]] = []
    upgrade_keywords = hotel_budget_upgrade_keywords(request)
    if upgrade_keywords:
        groups.append({"bucket": "hotel_budget_upgrade", "keywords": upgrade_keywords})
    groups.append({"bucket": "hotel_base", "keywords": unique_strings([keyword, "酒店"])})
    return groups


def hotel_budget_upgrade_keywords(request: TripRequest) -> List[str]:
    """预算较宽时补高价住宿关键词，但不突破明确经济型住宿请求。"""
    budget_level = request.budget_constraint.budget_level or ""
    accommodation = request.accommodation or ""
    if budget_level not in HOTEL_BUDGET_UPGRADE_KEYWORDS:
        return []
    if any(keyword in accommodation for keyword in ["经济", "快捷", "青年"]):
        return []

    keywords = list(HOTEL_BUDGET_UPGRADE_KEYWORDS.get(budget_level, []))
    if "民宿" in accommodation:
        keywords = ["精品民宿", "高端民宿", "设计师民宿", "度假民宿"] + keywords
    elif "亲子" in accommodation:
        keywords = ["高端亲子酒店", "亲子度假酒店"] + keywords
    elif "舒适" in accommodation:
        keywords = ["精品酒店", "中高端酒店"] + keywords
    elif "高端" in accommodation:
        keywords = ["高端酒店", "五星级酒店", "豪华酒店"] + keywords
    return unique_strings(keywords)


def build_attraction_preference_keywords(preferences: List[str]) -> List[str]:
    """把用户偏好转成景点侧关键词，避免把餐饮偏好直接搜成餐厅。"""
    primary_keywords: List[str] = []
    secondary_keywords: List[str] = []
    fallback_keywords: List[str] = []
    for item in preferences:
        mapped = attraction_keywords_for_preference(item)
        if mapped:
            primary_keywords.append(mapped[0])
            secondary_keywords.extend(mapped[1:])
        else:
            fallback_keywords.append(item)
    return unique_strings(primary_keywords + secondary_keywords + fallback_keywords)


def attraction_keywords_for_preference(preference: str) -> List[str]:
    """返回单个偏好的景点侧搜索词；精确标签优先于包含关系。"""
    if preference in ATTRACTION_PREFERENCE_KEYWORD_MAP:
        return ATTRACTION_PREFERENCE_KEYWORD_MAP[preference]

    keywords: List[str] = []
    for key, values in ATTRACTION_PREFERENCE_KEYWORD_MAP.items():
        if key in preference:
            keywords.extend(values)
    return unique_strings(keywords)


def build_food_keyword_groups(request: TripRequest) -> List[Dict[str, Any]]:
    """构造分桶餐饮搜索关键词。

    餐饮和景点不一样：Planner 每天都要安排午晚餐，只给一组全城
    “特色餐厅/本地菜”候选很容易不够用。这里先不接周边搜索 API，
    而是用可审计的多关键词分桶把候选池做厚。
    """
    preferences = positive_preference_tags(request)
    food_constraints = infer_food_constraints(request)
    groups: List[Dict[str, Any]] = []

    diet = food_constraints["diet"]
    if diet and diet != "无":
        append_food_group(groups, "food_diet", [diet, f"{diet}餐厅"])

    append_food_group(groups, "food_breakfast", breakfast_keywords_for_diet(diet))

    preference_keywords = []
    for item in preferences:
        if item in FOOD_PREFERENCE_KEYWORD_MAP:
            preference_keywords.extend(FOOD_PREFERENCE_KEYWORD_MAP[item])
        elif any(word in item for word in ["美食", "餐", "菜", "咖啡", "夜市", "小吃"]):
            preference_keywords.append(item)
    append_food_group(groups, "food_preference", preference_keywords)

    companion_type = request.party.companion_type or ""
    append_food_group(groups, "food_companion", FOOD_COMPANION_KEYWORDS.get(companion_type, []))

    budget_level = request.budget_constraint.budget_level or ""
    append_food_group(groups, "food_budget", FOOD_BUDGET_KEYWORDS.get(budget_level, []))
    append_food_group(groups, "food_budget_upgrade", build_budget_upgrade_keywords(request, "food"))
    append_food_group(groups, "food_base", FOOD_BASE_KEYWORDS)
    return groups


def breakfast_keywords_for_diet(diet: str) -> List[str]:
    """早餐单独召回，饮食约束明确时优先尝试约束早餐。"""
    keywords = []
    if diet and diet != "无":
        keywords.extend([f"{diet}早餐", f"{diet}早点"])
    keywords.extend(FOOD_BREAKFAST_KEYWORDS)
    return keywords


def append_food_group(groups: List[Dict[str, Any]], bucket: str, keywords: List[str]) -> None:
    """添加一个非空餐饮关键词分桶。"""
    cleaned = unique_strings(keywords)
    if cleaned:
        groups.append({"bucket": bucket, "keywords": cleaned})


def annotate_food_pois(rows: List[Dict[str, Any]], request: TripRequest) -> List[Dict[str, Any]]:
    """给餐饮候选补餐别、口味和忌口风险标签。"""
    food_constraints = infer_food_constraints(request)
    results = []
    for row in rows:
        item = dict(row)
        text = food_text(item)
        item["meal_roles"] = infer_meal_roles(text)
        item["cuisine_tags"] = infer_cuisine_tags(text)
        item["diet_tags"] = infer_diet_tags(text)
        item["avoid_risk_keywords"] = [keyword for keyword in food_constraints["avoid"] if keyword in text]
        results.append(item)
    return results


def filter_food_by_constraints(rows: List[Dict[str, Any]], request: TripRequest) -> List[Dict[str, Any]]:
    """过滤明显触犯忌口/过敏约束的餐饮候选。"""
    avoid = set(infer_food_constraints(request)["avoid"])
    if not avoid:
        return rows
    results = []
    for row in rows:
        text = food_text(row)
        if any(keyword in text for keyword in avoid):
            continue
        results.append(row)
    return results


def food_text(row: Dict[str, Any]) -> str:
    """拼出用于餐饮标签判断的短文本。"""
    return ";".join(
        str(row.get(key) or "")
        for key in ["name", "type", "address", "source_keyword", "source_bucket"]
    )


def infer_meal_roles(text: str) -> List[str]:
    """从餐饮关键词粗判适用餐别。"""
    breakfast_keywords = ["早餐", "早点", "早茶", "包子", "粥", "豆浆", "油条", "糕点"]
    flexible_keywords = ["咖啡", "小吃", "简餐", "快餐", "面馆", "粉店", "馄饨"]
    lunch_dinner_keywords = [
        "餐厅",
        "中餐厅",
        "西餐厅",
        "酒楼",
        "饭店",
        "火锅",
        "料理",
        "菜",
        "宴",
        "商务",
        "高端",
        "精致",
        "品质",
        "私房",
        "融合",
        "黑珍珠",
        "米其林",
        "法餐",
        "omakase",
        "food_budget",
        "food_budget_upgrade",
    ]

    if "food_breakfast" in text:
        if any(keyword in text for keyword in flexible_keywords):
            return ["breakfast", "lunch", "dinner"]
        return ["breakfast"]
    if any(keyword in text for keyword in lunch_dinner_keywords):
        return ["lunch", "dinner"]
    if any(keyword in text for keyword in breakfast_keywords):
        return ["breakfast"]
    if any(keyword in text for keyword in flexible_keywords):
        return ["breakfast", "lunch", "dinner"]
    return ["lunch", "dinner"]


def infer_cuisine_tags(text: str) -> List[str]:
    """抽取给 Planner 看的餐饮标签。"""
    return [keyword for keyword in FOOD_TAG_KEYWORDS if keyword in text]


def infer_diet_tags(text: str) -> List[str]:
    """抽取饮食约束相关标签。"""
    return [keyword for keyword in ["清真", "素食", "少辣"] if keyword in text]


def positive_preference_tags(request: TripRequest) -> List[str]:
    """过滤掉明显负向表达，避免拿“海鲜过敏”这类词去正向搜POI。"""
    return [
        item.strip()
        for item in request.preferences
        if item and item.strip() and not is_negative_preference(item)
    ]


def is_negative_preference(value: str) -> bool:
    """判断偏好标签是否其实是负向约束。"""
    text = str(value or "").strip()
    return any(marker in text for marker in NEGATIVE_PREFERENCE_MARKERS)


def avoids_expensive_food(request: TripRequest) -> bool:
    """用户明确避开高价餐厅时，不做餐饮高价补召回。"""
    text = " ".join(request.preferences + [request.free_text_input or ""])
    return any(
        marker in text
        for marker in ["高价餐厅", "高价饭店", "高消费餐厅", "贵餐厅", "太贵的餐厅"]
    )


def normalize_pois(
    raw: Dict[str, Any],
    source_keyword: str,
    source_role: str,
    require_location: bool,
    source_bucket: str,
) -> List[Dict[str, Any]]:
    """把高德POI结果压成Planner可读的小字段集合。"""
    rows = []
    for poi in raw.get("pois", []):
        location = parse_location(poi.get("location"))
        if require_location and not location:
            continue
        biz_ext = poi.get("biz_ext") or {}
        photos = poi.get("photos") or []
        photo_urls = [photo.get("url") for photo in photos if photo.get("url")]
        rows.append(
            {
                "id": poi.get("id", ""),
                "name": poi.get("name", ""),
                "type": poi.get("type", ""),
                "typecode": poi.get("typecode", ""),
                "address": poi.get("address") if isinstance(poi.get("address"), str) else "",
                "location": location,
                "cityname": poi.get("cityname", ""),
                "adname": poi.get("adname", ""),
                "rating": biz_ext.get("rating", ""),
                "cost": biz_ext.get("cost", ""),
                # Planner不需要图片URL，保留数量即可，避免长URL把上下文撑大。
                "photo_count": len(photo_urls),
                "source_keyword": source_keyword,
                "source_role": source_role,
                "source_bucket": source_bucket or source_role,
            }
        )
    return rows


def merge_poi_buckets(buckets: List[List[Dict[str, Any]]], limit: int) -> List[Dict[str, Any]]:
    """合并不同召回池，保留前序池子的优先级并去重。"""
    rows = []
    for bucket in buckets:
        rows.extend(bucket)
    return dedupe_pois(rows)[:limit]


def filter_pois(rows: List[Dict[str, Any]], source_role: str) -> List[Dict[str, Any]]:
    """按用途过滤明显不适合旅行规划的POI。"""
    return [row for row in rows if not is_noise_poi(row, source_role)]


def is_noise_poi(row: Dict[str, Any], source_role: str) -> bool:
    """判断POI是否是当前用途下的噪声。"""
    name = str(row.get("name") or "")
    poi_type = str(row.get("type") or "")
    text = f"{name};{poi_type};{row.get('address') or ''}"

    if source_role in {"scenic", "experience"}:
        if any(keyword in text for keyword in POI_NOISE_KEYWORDS):
            return True

    if source_role == "scenic":
        return not contains_any(poi_type, SCENIC_ALLOWED_TYPE_KEYWORDS)

    if source_role == "experience":
        return not contains_any(poi_type, EXPERIENCE_ALLOWED_TYPE_KEYWORDS)

    if source_role == "food":
        # 餐饮候选优先只保留真正餐厅；水产市场/批发市场给Planner意义不大。
        return "餐饮服务" not in poi_type

    if source_role == "hotel":
        return "住宿服务" not in poi_type

    return False


def rank_pois(rows: List[Dict[str, Any]], source_role: str) -> List[Dict[str, Any]]:
    """按质量信号排序，优先给Planner更干净的候选。"""
    return sorted(rows, key=lambda row: poi_rank_key(row, source_role), reverse=True)


def poi_rank_key(row: Dict[str, Any], source_role: str) -> tuple:
    """POI排序分数。"""
    rating = parse_float(row.get("rating"))
    has_cost = 1 if parse_float(row.get("cost")) is not None else 0
    has_location = 1 if row.get("location") else 0
    has_address = 1 if row.get("address") else 0

    if source_role == "food":
        return (has_cost, rating or 0, has_location, has_address)

    if source_role == "hotel":
        return (rating or 0, has_location, has_address, has_cost)

    return (rating or 0, has_location, has_address, has_cost)


def contains_any(text: str, keywords: List[str]) -> bool:
    """判断文本是否包含任意关键词。"""
    return any(keyword in text for keyword in keywords)


def parse_float(value: Any) -> Optional[float]:
    """解析高德biz_ext里的评分/价格。"""
    if value in (None, "", []):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_location(value: Any) -> Optional[Dict[str, float]]:
    """解析高德 location 字段。"""
    if not value or not isinstance(value, str) or "," not in value:
        return None
    try:
        longitude, latitude = value.split(",", 1)
        return {"longitude": float(longitude), "latitude": float(latitude)}
    except ValueError:
        return None


def dedupe_pois(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按POI id/name/address去重，保持原始顺序。"""
    seen = set()
    results = []
    for row in rows:
        key = row.get("id") or f"{row.get('name')}|{row.get('address')}"
        if key in seen:
            continue
        seen.add(key)
        results.append(row)
    return results


def unique_strings(values: List[str]) -> List[str]:
    """字符串去重并过滤空值。"""
    results = []
    seen = set()
    for value in values:
        value = value.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        results.append(value)
    return results


def infer_pace(request: TripRequest) -> str:
    """从自由文本和同行类型推断节奏。"""
    text = " ".join(request.preferences + [request.free_text_input or ""])
    if any(word in text for word in ["慢", "轻松", "不累", "休闲", "少走路"]):
        return "慢节奏"
    if any(word in text for word in ["紧凑", "多玩", "特种兵", "打卡"]):
        return "紧凑"
    if request.party.children > 0 or request.party.elders > 0:
        return "慢节奏"
    return "未指定"


def infer_food_constraints(request: TripRequest) -> Dict[str, Any]:
    """从偏好和自由文本中拆出饮食偏好与忌口约束。"""
    text = " ".join(request.preferences + [request.free_text_input or ""])

    avoid = []
    for keyword in FOOD_AVOID_KEYWORDS:
        if mentions_food_avoidance(text, keyword):
            avoid.append(keyword)

    diet = "无"
    for keyword in DIET_PREFERENCE_KEYWORDS:
        if keyword in avoid:
            continue
        if keyword in text:
            diet = keyword
            break

    return {"diet": diet, "avoid": avoid}


def mentions_food_avoidance(text: str, keyword: str) -> bool:
    """判断某个食物词是否出现在负向饮食表达中。"""
    if keyword not in text:
        return False
    for marker in FOOD_AVOID_MARKERS:
        if f"{marker}{keyword}" in text or f"{keyword}{marker}" in text:
            return True
    return False
