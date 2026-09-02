"""Local curated POI tables for planner context recall gaps."""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_HIGH_END_POI_TABLE_PATH = Path(__file__).with_name("high_end_poi_table.json")
HIGH_END_POI_TABLE_PATH = Path(
    os.getenv("PLANNER_HIGH_END_POI_TABLE_PATH", str(DEFAULT_HIGH_END_POI_TABLE_PATH))
)

HIGH_BUDGET_LEVELS = {"comfortable", "premium", "luxury"}
HOTEL_HIGH_BUDGET_LEVELS = {"premium", "luxury"}
HIGH_BUDGET_LEVELS_BY_CATEGORY = {
    "food": HIGH_BUDGET_LEVELS,
    "scenic": HIGH_BUDGET_LEVELS,
    "experience": HIGH_BUDGET_LEVELS,
    "hotel": HOTEL_HIGH_BUDGET_LEVELS,
}
DEFAULT_SOURCE_BUCKET = {
    "food": "food_budget_upgrade",
    "hotel": "hotel_budget_upgrade",
    "scenic": "attraction_budget_upgrade",
    "experience": "experience_budget_upgrade",
}
DEFAULT_SOURCE_KEYWORD = {
    "food": "高端餐厅",
    "hotel": "高端酒店",
    "scenic": "大型景区",
    "experience": "高端体验",
}


def should_use_high_end_local_pois(budget_level: str, category: str = "") -> bool:
    """Return whether curated high-end POIs should enter context."""
    levels = HIGH_BUDGET_LEVELS_BY_CATEGORY.get(category, HIGH_BUDGET_LEVELS)
    return budget_level in levels


def local_high_end_pois(city: str, category: str, source_bucket: str = "") -> List[Dict[str, Any]]:
    """Load curated high-end POIs for one city/category as normal POI rows."""
    city_key = _city_key(city)
    table = load_high_end_poi_table()
    city_data = table.get(city_key) or table.get(city_key.removesuffix("市")) or {}
    rows = city_data.get(category) or []
    bucket = source_bucket or DEFAULT_SOURCE_BUCKET.get(category, category)

    results = []
    for row in rows:
        item = dict(row)
        item.setdefault("id", f"local-high-end:{city_key}:{category}:{item.get('name') or len(results)}")
        item.setdefault("source_role", category)
        item.setdefault("source_bucket", bucket)
        item.setdefault("source_keyword", DEFAULT_SOURCE_KEYWORD.get(category, category))
        item.setdefault("photo_count", 0)
        item["source_bucket"] = bucket
        item["local_table"] = "high_end_poi_table"
        results.append(item)
    return results


@lru_cache(maxsize=1)
def load_high_end_poi_table() -> Dict[str, Any]:
    """Load curated POI table. Missing or invalid files degrade to no rows."""
    path = _resolve_path(HIGH_END_POI_TABLE_PATH)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        print(f"⚠️  高端POI表解析失败: {path} ({exc})")
        return {}
    return data.get("cities") or {}


def _resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parents[3] / path


def _city_key(city: str) -> str:
    text = str(city or "").strip()
    return text or "unknown"
