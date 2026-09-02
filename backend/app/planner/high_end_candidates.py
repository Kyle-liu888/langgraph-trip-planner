"""High-end POI verification and budget-aware context ranking."""

import re
from typing import Any, Dict, List, Tuple

from ..models.schemas import TripRequest


HIGH_BUDGET_LEVELS = {"comfortable", "premium", "luxury"}
HOTEL_HIGH_BUDGET_LEVELS = {"premium", "luxury"}

FOOD_VERIFIED_MIN = {
    "comfortable": 120,
    "premium": 180,
    "luxury": 260,
}
FOOD_CONTEXT_MIN = {
    "comfortable": 80,
    "premium": 120,
    "luxury": 180,
}

HOTEL_VERIFIED_MIN = {
    "premium": 900,
    "luxury": 1200,
}
HOTEL_CONTEXT_MIN = {
    "premium": 700,
    "luxury": 900,
}
COMFORTABLE_HOTEL_TARGET_MIN = 350
COMFORTABLE_HOTEL_TARGET_MAX = 700
COMFORTABLE_HOTEL_TARGET_MID = 550

FOOD_HIGH_END_KEYWORDS = [
    "米其林",
    "黑珍珠",
    "omakase",
    "Omakase",
    "法餐",
    "高端餐厅",
    "高端",
    "商务宴请",
    "商务餐厅",
    "私房菜",
    "精致餐厅",
    "品质餐厅",
    "创意菜",
]
FOOD_QUALITY_LOCAL_KEYWORDS = [
    "本地菜",
    "特色餐厅",
    "老字号",
    "中餐厅",
    "酒楼",
    "饭店",
    "私房菜",
    "融合菜",
    "海鲜",
    "火锅",
    "地方菜",
]
FOOD_LIGHT_OR_LOW_END_KEYWORDS = [
    "早餐",
    "早点",
    "包子",
    "粥",
    "豆浆",
    "油条",
    "快餐",
    "简餐",
    "小吃",
    "面馆",
    "粉店",
    "咖啡",
    "奶茶",
]
HOTEL_HIGH_END_KEYWORDS = [
    "奢华",
    "豪华",
    "五星",
    "五星级",
    "高端酒店",
    "高端",
    "度假酒店",
    "度假",
    "精品酒店",
    "中高端",
    "四星",
    "四星级",
]
HOTEL_LOW_END_KEYWORDS = [
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
TOP_LUXURY_HOTEL_BRANDS = [
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
]


def rank_food_for_budget_context(
    rows: List[Dict[str, Any]],
    request: TripRequest,
    limit: int | None = None,
) -> List[Dict[str, Any]]:
    """Verify, dedupe and rank food POIs for higher-budget requests."""
    budget_level = _budget_level(request)
    annotated = [annotate_food_candidate(row, budget_level) for row in rows]
    annotated = dedupe_candidates(annotated, _food_dedupe_key, _food_priority)

    if budget_level not in HIGH_BUDGET_LEVELS:
        return assign_budget_ranks(annotated[:limit] if limit else annotated)

    breakfast_rows = [row for row in annotated if is_breakfast_row(row)]
    meal_rows = [row for row in annotated if not is_breakfast_row(row)]
    ranked_breakfast = sorted(breakfast_rows, key=_breakfast_priority)
    if limit is None:
        ranked_meals = rank_food_meals_with_diversity(meal_rows, budget_level, None)
        return assign_budget_ranks(ranked_meals + ranked_breakfast)

    meal_limit = limit
    ranked_meals = rank_food_meals_with_diversity(meal_rows, budget_level, meal_limit)
    ranked = ranked_meals[:meal_limit] + ranked_breakfast
    return assign_budget_ranks(ranked)


def rank_food_meals_with_diversity(
    rows: List[Dict[str, Any]],
    budget_level: str,
    limit: int | None,
) -> List[Dict[str, Any]]:
    """Rank lunch/dinner candidates by budget buckets without hard price filtering."""
    if not rows:
        return []

    if limit is None:
        limit = len(rows)

    verified = [row for row in rows if row.get("high_end_verified")]
    signal = [
        row
        for row in rows
        if not row.get("high_end_verified") and _is_food_high_end_signal(row)
    ]
    quality_local = [
        row
        for row in rows
        if not row.get("high_end_verified")
        and not _is_food_high_end_signal(row)
        and _is_quality_local_food(row)
    ]
    if budget_level == "luxury":
        quotas = (0.45, 0.35, 0.15)
    elif budget_level == "premium":
        quotas = (0.35, 0.30, 0.25)
    else:
        quotas = (0.25, 0.30, 0.35)

    selected: List[Dict[str, Any]] = []
    selected_keys: set[str] = set()
    bucket_specs = [
        (verified, _food_priority, max(2, int(round(limit * quotas[0]))), "verified_high_price"),
        (signal, _food_priority, max(3, int(round(limit * quotas[1]))), "high_end_signal"),
        (quality_local, _quality_local_food_priority, max(3, int(round(limit * quotas[2]))), "quality_local"),
    ]
    for bucket_rows, priority_fn, quota, bucket_name in bucket_specs:
        _take_food_bucket(bucket_rows, priority_fn, quota, bucket_name, selected, selected_keys)

    remaining = [
        row
        for row in rows
        if _food_dedupe_key(row) not in selected_keys
    ]
    _take_food_bucket(
        remaining,
        _food_diversity_fill_priority,
        limit - len(selected),
        "diversity_fill",
        selected,
        selected_keys,
    )
    return selected[:limit]


def _take_food_bucket(
    rows: List[Dict[str, Any]],
    priority_fn: Any,
    quota: int,
    bucket_name: str,
    selected: List[Dict[str, Any]],
    selected_keys: set[str],
) -> None:
    if quota <= 0:
        return
    for row in sorted(rows, key=priority_fn):
        key = _food_dedupe_key(row)
        if key in selected_keys:
            continue
        item = dict(row)
        item["food_candidate_bucket"] = bucket_name
        selected.append(item)
        selected_keys.add(key)
        if len([candidate for candidate in selected if candidate.get("food_candidate_bucket") == bucket_name]) >= quota:
            break


def rank_hotels_for_budget_context(
    rows: List[Dict[str, Any]],
    request: TripRequest,
    limit: int | None = None,
) -> List[Dict[str, Any]]:
    """Verify, dedupe and rank hotel POIs for higher-budget requests."""
    budget_level = _budget_level(request)
    annotated = [annotate_hotel_candidate(row, budget_level) for row in rows]
    annotated = dedupe_candidates(annotated, _hotel_dedupe_key, _hotel_priority)

    if budget_level == "comfortable":
        ranked = sorted(annotated, key=_comfortable_hotel_priority)
        if limit is not None:
            ranked = ranked[:limit]
        return assign_budget_ranks(ranked)

    if budget_level not in HOTEL_HIGH_BUDGET_LEVELS:
        ranked = annotated[:limit] if limit else annotated
        return assign_budget_ranks(ranked)

    context_min = HOTEL_CONTEXT_MIN.get(budget_level, 0)
    kept = [row for row in annotated if _hotel_context_keep(row, context_min)]
    if not kept and annotated:
        fallback = sorted(annotated, key=_hotel_rescue_priority)[: min(len(annotated), limit or 1)]
        for row in fallback:
            row["budget_filter_relaxed"] = True
            row["verification_reason"] = row.get("verification_reason") or "rescued_for_hotel_coverage"
        kept = fallback

    ranked = sorted(kept, key=_hotel_priority)
    if limit is not None:
        ranked = ranked[:limit]
    return assign_budget_ranks(ranked)


def annotate_food_candidate(row: Dict[str, Any], budget_level: str) -> Dict[str, Any]:
    """Attach high-end verification metadata to one food candidate."""
    item = dict(row)
    if budget_level not in HIGH_BUDGET_LEVELS or is_breakfast_row(item):
        item.setdefault("price_confidence", _price_confidence(item.get("cost_source")))
        return item

    price = _number(item.get("meal_cost_hint"))
    verified_min = FOOD_VERIFIED_MIN.get(budget_level, 0)
    has_signal = _has_any(food_text(item), FOOD_HIGH_END_KEYWORDS) or _source_bucket(item) in {
        "food_budget",
        "food_budget_upgrade",
    }
    cost_source = str(item.get("cost_source") or "")

    if cost_source == "amap_cost" and price >= verified_min:
        item["high_end_verified"] = True
        item["price_confidence"] = "high"
        item["verification_reason"] = f"amap_cost_gte_{verified_min}"
    elif cost_source == "amap_cost" and has_signal and price < verified_min:
        item["price_confidence"] = "high"
        item["verification_reason"] = f"amap_cost_below_{verified_min}"
    elif cost_source in {"rule_estimated_high_end", "rule_estimated"} and has_signal and price >= verified_min:
        item["high_end_estimated"] = True
        item["price_confidence"] = "medium"
        item["verification_reason"] = f"high_end_signal_estimated_gte_{verified_min}"
    else:
        item["price_confidence"] = _price_confidence(cost_source)
    return item


def annotate_hotel_candidate(row: Dict[str, Any], budget_level: str) -> Dict[str, Any]:
    """Attach high-end verification metadata to one hotel candidate."""
    item = dict(row)
    if budget_level not in HOTEL_HIGH_BUDGET_LEVELS:
        item.setdefault("price_confidence", _price_confidence(item.get("cost_source")))
        return item

    price = _number(item.get("estimated_cost_hint"))
    verified_min = HOTEL_VERIFIED_MIN.get(budget_level, 0)
    text = hotel_text(item)
    has_signal = _has_any(text, HOTEL_HIGH_END_KEYWORDS + TOP_LUXURY_HOTEL_BRANDS)
    has_low_end_signal = _has_any(hotel_low_end_text(item), HOTEL_LOW_END_KEYWORDS)
    cost_source = str(item.get("cost_source") or "")

    if cost_source == "amap_cost" and price >= verified_min:
        item["high_end_verified"] = True
        item["price_confidence"] = "high"
        item["verification_reason"] = f"amap_cost_gte_{verified_min}"
    elif cost_source == "amap_cost" and has_signal and price < verified_min:
        item["price_confidence"] = "high"
        item["verification_reason"] = f"amap_cost_below_{verified_min}"
    elif cost_source == "rule_estimated_high_end" and price >= verified_min and has_signal and not has_low_end_signal:
        item["high_end_estimated"] = True
        item["price_confidence"] = "medium"
        item["verification_reason"] = f"high_end_signal_estimated_gte_{verified_min}"
    else:
        item["price_confidence"] = _price_confidence(cost_source)
    return item


def summarize_high_end_candidates(rows: List[Dict[str, Any]], price_key: str) -> Dict[str, Any]:
    """Return a compact audit summary for raw context inspection."""
    prices = sorted(_number(row.get(price_key)) for row in rows if _number(row.get(price_key)) > 0)
    return {
        "count": len(rows),
        "high_end_verified": sum(1 for row in rows if row.get("high_end_verified")),
        "high_end_estimated": sum(1 for row in rows if row.get("high_end_estimated")),
        "relaxed": sum(1 for row in rows if row.get("budget_filter_relaxed")),
        "price_p50": percentile(prices, 0.5),
        "price_p90": percentile(prices, 0.9),
        "price_max": max(prices) if prices else None,
    }


def dedupe_candidates(
    rows: List[Dict[str, Any]],
    key_fn: Any,
    priority_fn: Any,
) -> List[Dict[str, Any]]:
    """Dedupe by normalized name while keeping the best candidate per name."""
    best: Dict[str, Tuple[Tuple[Any, ...], int, Dict[str, Any]]] = {}
    passthrough: List[Tuple[int, Dict[str, Any]]] = []
    for index, row in enumerate(rows):
        key = key_fn(row)
        if not key:
            passthrough.append((index, row))
            continue
        score = priority_fn(row)
        if key not in best or score < best[key][0]:
            best[key] = (score, index, row)

    chosen = [(index, row) for _, index, row in best.values()] + passthrough
    return [row for _, row in sorted(chosen, key=lambda item: item[0])]


def assign_budget_ranks(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach a stable 1-based rank after final context ordering."""
    results = []
    for index, row in enumerate(rows, start=1):
        item = dict(row)
        item["budget_rank"] = index
        results.append(item)
    return results


def strip_budget_context_metadata(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove internal ranking metadata before exposing PlannerContext."""
    internal_keys = {
        "high_end_verified",
        "high_end_estimated",
        "price_confidence",
        "verification_reason",
        "budget_filter_relaxed",
        "budget_rank",
        "local_table",
        "source_provider",
        "source_query",
        "source_collected_at",
        "food_candidate_bucket",
    }
    results = []
    for row in rows:
        item = dict(row)
        for key in internal_keys:
            item.pop(key, None)
        results.append(item)
    return results


def percentile(values: List[int], ratio: float) -> int | None:
    if not values:
        return None
    index = min(len(values) - 1, max(0, int(round((len(values) - 1) * ratio))))
    return values[index]


def is_breakfast_row(row: Dict[str, Any]) -> bool:
    roles = {str(role or "").strip().lower() for role in row.get("meal_roles") or []}
    return _source_bucket(row) == "food_breakfast" or roles == {"breakfast"}


def food_text(row: Dict[str, Any]) -> str:
    values = [
        row.get("name"),
        row.get("type"),
        row.get("address"),
        row.get("source_keyword"),
        row.get("source_bucket"),
        " ".join(str(tag) for tag in row.get("cuisine_tags") or []),
    ]
    return ";".join(str(value or "") for value in values)


def hotel_text(row: Dict[str, Any]) -> str:
    values = [
        row.get("name"),
        row.get("type"),
        row.get("address"),
    ]
    if row.get("local_table") == "high_end_poi_table":
        values.extend([row.get("source_keyword"), row.get("source_bucket")])
    return ";".join(str(value or "") for value in values)


def hotel_low_end_text(row: Dict[str, Any]) -> str:
    values = [row.get("name"), row.get("type"), row.get("source_keyword")]
    return ";".join(str(value or "") for value in values)


def _food_context_keep(row: Dict[str, Any], context_min: int) -> bool:
    return (
        bool(row.get("high_end_verified"))
        or bool(row.get("high_end_estimated"))
        or _number(row.get("meal_cost_hint")) >= context_min
    )


def _is_food_high_end_signal(row: Dict[str, Any]) -> bool:
    return (
        bool(row.get("high_end_estimated"))
        or row.get("local_table") == "high_end_poi_table"
        or _source_bucket(row) in {"food_budget", "food_budget_upgrade"}
        or _has_any(food_text(row), FOOD_HIGH_END_KEYWORDS)
    )


def _is_quality_local_food(row: Dict[str, Any]) -> bool:
    text = food_text(row)
    bucket = _source_bucket(row)
    if _has_any(text, FOOD_LIGHT_OR_LOW_END_KEYWORDS):
        return False
    if _has_any(text, FOOD_QUALITY_LOCAL_KEYWORDS):
        return True
    if bucket in {"food_base", "food_preference", "food_companion", "food_diet"} and _rating(row) >= 4.3:
        return True
    return False


def _hotel_context_keep(row: Dict[str, Any], context_min: int) -> bool:
    if _has_any(hotel_low_end_text(row), HOTEL_LOW_END_KEYWORDS) and not row.get("high_end_verified"):
        return False
    has_high_end_signal = _has_any(hotel_text(row), HOTEL_HIGH_END_KEYWORDS + TOP_LUXURY_HOTEL_BRANDS)
    if str(row.get("cost_source") or "") != "amap_cost" and not has_high_end_signal:
        return False
    return (
        bool(row.get("high_end_verified"))
        or bool(row.get("high_end_estimated"))
        or _number(row.get("estimated_cost_hint")) >= context_min
    )


def _food_priority(row: Dict[str, Any]) -> Tuple[Any, ...]:
    return (
        _verification_rank(row),
        _source_rank(row),
        _confidence_rank(row),
        -_number(row.get("meal_cost_hint")),
        -_rating(row),
        str(row.get("name") or ""),
    )


def _hotel_priority(row: Dict[str, Any]) -> Tuple[Any, ...]:
    return (
        _verification_rank(row),
        _source_rank(row),
        _confidence_rank(row),
        -_number(row.get("estimated_cost_hint")),
        -_rating(row),
        str(row.get("name") or ""),
    )


def _comfortable_hotel_priority(row: Dict[str, Any]) -> Tuple[Any, ...]:
    price = _number(row.get("estimated_cost_hint"))
    if COMFORTABLE_HOTEL_TARGET_MIN <= price <= COMFORTABLE_HOTEL_TARGET_MAX:
        price_band = 0
    elif price and price < COMFORTABLE_HOTEL_TARGET_MIN:
        price_band = 1
    else:
        price_band = 2
    low_end_signal = _has_any(hotel_low_end_text(row), HOTEL_LOW_END_KEYWORDS)
    return (
        price_band,
        low_end_signal,
        abs(price - COMFORTABLE_HOTEL_TARGET_MID) if price else 99999,
        _source_rank(row),
        -_rating(row),
        str(row.get("name") or ""),
    )


def _food_rescue_priority(row: Dict[str, Any]) -> Tuple[Any, ...]:
    return (-_number(row.get("meal_cost_hint")), _source_rank(row), -_rating(row))


def _hotel_rescue_priority(row: Dict[str, Any]) -> Tuple[Any, ...]:
    return (-_number(row.get("estimated_cost_hint")), _source_rank(row), -_rating(row))


def _breakfast_priority(row: Dict[str, Any]) -> Tuple[Any, ...]:
    return (_source_rank(row), -_rating(row), _number(row.get("meal_cost_hint")))


def _quality_local_food_priority(row: Dict[str, Any]) -> Tuple[Any, ...]:
    return (
        _source_rank(row),
        -_rating(row),
        _number(row.get("meal_cost_hint")),
        str(row.get("name") or ""),
    )


def _food_diversity_fill_priority(row: Dict[str, Any]) -> Tuple[Any, ...]:
    return (
        _is_light_or_low_end_food(row),
        _source_rank(row),
        -_rating(row),
        -_number(row.get("meal_cost_hint")),
        str(row.get("name") or ""),
    )


def _is_light_or_low_end_food(row: Dict[str, Any]) -> bool:
    return _has_any(food_text(row), FOOD_LIGHT_OR_LOW_END_KEYWORDS)


def _verification_rank(row: Dict[str, Any]) -> int:
    if row.get("high_end_verified"):
        return 0
    if row.get("high_end_estimated"):
        return 1
    return 2


def _source_rank(row: Dict[str, Any]) -> int:
    if row.get("local_table") == "high_end_poi_table":
        return -1
    bucket = _source_bucket(row)
    if bucket in {"food_budget_upgrade", "hotel_budget_upgrade"}:
        return 0
    if bucket in {"food_budget", "hotel_base"}:
        return 1
    return 2


def _confidence_rank(row: Dict[str, Any]) -> int:
    confidence = str(row.get("price_confidence") or "")
    if confidence == "high":
        return 0
    if confidence == "medium":
        return 1
    return 2


def _food_dedupe_key(row: Dict[str, Any]) -> str:
    return _normalize_name(row.get("name"))


def _hotel_dedupe_key(row: Dict[str, Any]) -> str:
    return _normalize_name(row.get("name"))


def _normalize_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s·•\-_\(\)（）【】\[\]<>《》「」『』]", "", text)
    return text


def _budget_level(request: TripRequest) -> str:
    return str(request.budget_constraint.budget_level or "")


def _source_bucket(row: Dict[str, Any]) -> str:
    return str(row.get("source_bucket") or "")


def _has_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _number(value: Any) -> int:
    if value in (None, "", []):
        return 0
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return 0


def _rating(row: Dict[str, Any]) -> float:
    try:
        return float(row.get("rating") or 0)
    except (TypeError, ValueError):
        return 0.0


def _price_confidence(cost_source: Any) -> str:
    if cost_source == "amap_cost":
        return "high"
    if cost_source == "rule_estimated_high_end":
        return "medium"
    return "low"
