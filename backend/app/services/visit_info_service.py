"""Read-only visit facts; independent of Planner, budgets and persisted trips."""
from collections import OrderedDict
from copy import deepcopy
from datetime import date, datetime
from functools import lru_cache
import json
from pathlib import Path
from threading import Lock
from time import monotonic
from urllib.parse import urlencode, urlsplit
from zoneinfo import ZoneInfo

import httpx

from ..config import get_settings
from ..observability import logger
from ..planner.amap import AmapPlannerClient
from .poi_photo_service import get_poi_photo_service, matches, normalized

CHINA = ZoneInfo("Asia/Shanghai")
SOURCE_FILE = Path(__file__).with_name("official_visit_sources.json")
ALLOWED_OFFICIAL_HOSTS = {"www.dpm.org.cn", "summerpalace.net.cn", "www.tiantanpark.cn"}
NOTICE = "节假日、临时闭馆以官方公告为准；本次规划未自动校验闭馆日期"


def now_china():
    return datetime.now(CHINA)


def safe_official_url(value):
    try:
        parsed = urlsplit(value)
        return parsed.scheme in {"http", "https"} and parsed.hostname in ALLOWED_OFFICIAL_HOSTS and not parsed.username and not parsed.password
    except (ValueError, TypeError):
        return False


@lru_cache(maxsize=1)
def official_registry():
    items = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))["items"]
    for item in items:
        date.fromisoformat(item["verified_at"])
        if not all(safe_official_url(link["url"]) for link in item["links"]):
            raise ValueError("Invalid official source URL")
    return items


def official_source(name, city, poi_id):
    for item in official_registry():
        if normalized(city).removesuffix("市") != normalized(item["city"]).removesuffix("市"):
            continue
        if normalized(name) not in [normalized(n) for n in item["names"]]:
            continue
        if poi_id and item["poi_ids"] and poi_id not in item["poi_ids"]:
            continue
        return {k: deepcopy(item[k]) for k in ("source_name", "verified_at", "reservation_note", "links")}
    return None


def text_field(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


class VisitLookupError(Exception):
    def __init__(self, status):
        self.status = status


class VisitInfoService:
    def __init__(self, api_key):
        self.api_key = api_key
        self.cache = OrderedDict()
        self.lock = Lock()

    def request_detail(self, poi_id):
        if not self.api_key:
            raise VisitLookupError("permission_denied")
        AmapPlannerClient._wait_for_amap_slot()
        response = httpx.get("https://restapi.amap.com/v5/place/detail",
                            params={"key": self.api_key, "id": poi_id, "show_fields": "business"},
                            timeout=8)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "1":
            denied = str(data.get("infocode")) in {"10001", "10002", "10005", "10007", "10009", "10012", "10013", "10041", "10045", "10046"}
            raise VisitLookupError("permission_denied" if denied else "unavailable")
        return data.get("pois") or []

    def lookup(self, name, city, poi_id, longitude, latitude):
        if not city.strip():
            return {"status": "unmatched"}
        if not poi_id:
            if longitude is None or latitude is None:
                return {"status": "unmatched"}
            rows = get_poi_photo_service().request("/place/text", {
                "keywords": name, "city": city, "citylimit": "true",
                "extensions": "base", "offset": 10, "page": 1,
            })
            found = {r.get("id"): r for r in rows if r.get("id") and matches(r, name, city, longitude, latitude)}
            if len(found) != 1:
                return {"status": "unmatched"}
            poi_id = next(iter(found))
        rows = self.request_detail(poi_id)
        found = [r for r in rows if r.get("id") == poi_id and matches(r, name, city, longitude, latitude)]
        if len(found) != 1:
            return {"status": "unmatched"}
        business = found[0].get("business")
        business = business if isinstance(business, dict) else {}
        today = text_field(business.get("opentime_today"))
        regular = text_field(business.get("opentime_week"))
        return {"status": "available" if today or regular else "no_data", "poi_id": poi_id,
                "today": today, "regular": regular}

    def resolve(self, name, city, poi_id="", longitude=None, latitude=None, visit_date=None):
        started = monotonic()
        key = (name, city, poi_id, longitude, latitude)
        now = now_china()
        cached = False
        with self.lock:
            item = self.cache.get(key)
            # Today's hours must not cross midnight through an otherwise valid cache.
            if item and item[0] > monotonic() and item[1]["queried_date"] == now.date().isoformat():
                data = deepcopy(item[1])
                self.cache.move_to_end(key)
                cached = True
        if not cached:
            try:
                data = self.lookup(name, city, poi_id, longitude, latitude)
            except VisitLookupError as exc:
                data = {"status": exc.status}
            except httpx.TimeoutException:
                data = {"status": "timeout"}
            except Exception as exc:
                logger.warning("poi.visit_info_failed", extra={"error_type": type(exc).__name__})
                data = {"status": "unavailable"}
            fetched = now_china()
            data.update(fetched_at=fetched.isoformat(), queried_date=fetched.date().isoformat())
            if data["status"] in {"available", "no_data", "unmatched"}:
                with self.lock:
                    self.cache[key] = (monotonic() + 900, deepcopy(data))
                    self.cache.move_to_end(key)
                    while len(self.cache) > 512:
                        self.cache.popitem(last=False)
        resolved_id = data.get("poi_id")
        official = official_source(name, city, resolved_id or poi_id)
        # An explicit contradictory match must never claim a verified official identity.
        if data["status"] == "unmatched":
            official = None
        is_same_day = visit_date is None or visit_date.isoformat() == data["queried_date"]
        today = data.get("today") if is_same_day else None
        regular = data.get("regular")
        status = data["status"]
        if status == "available" and not today and not regular:
            status = "no_data"
        result = {
            "status": status, "poi_id": resolved_id,
            "match_status": "matched" if resolved_id else ("unmatched" if status == "unmatched" else "unknown"),
            "visit_date": visit_date.isoformat() if visit_date else None,
            "opening": {"today": today, "today_date": data["queried_date"] if today else None,
                        "regular": regular, "scope": "reference_only"},
            "source_name": "高德地图 POI 2.0（参考信息，非景区官方确认）",
            "source_url": "https://uri.amap.com/marker?" + urlencode({"poiid": resolved_id, "name": name, "src": "trip-planner"}) if resolved_id else None,
            "fetched_at": data["fetched_at"], "upstream_updated_at": None,
            "official": official, "notice": NOTICE,
        }
        logger.info("poi.visit_info_resolved", extra={"visit_status": status, "cache_hit": cached, "elapsed_ms": round((monotonic() - started) * 1000)})
        return result


@lru_cache(maxsize=1)
def get_visit_info_service():
    return VisitInfoService(get_settings().secret_value("amap_api_key"))
