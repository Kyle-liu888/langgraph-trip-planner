"""Verified merchant cards: optional display enrichment, never planner input.

Name similarity is deliberately insufficient: branch names are retained and
contradictory evidence is rejected even when a POI ID has been supplied.
"""
from collections import OrderedDict
from copy import deepcopy
from datetime import date, datetime
from functools import lru_cache
import json
from math import asin, cos, isfinite, radians, sin, sqrt
from pathlib import Path
import re
from threading import Lock
from time import monotonic
from urllib.parse import parse_qsl, urlencode, urlsplit
from zoneinfo import ZoneInfo

import httpx

from ..config import get_settings
from ..observability import logger
from ..planner.amap import AmapPlannerClient
from .poi_photo_service import normalized

SOURCE_FILE = Path(__file__).with_name("merchant_sources.json")
CHINA = ZoneInfo("Asia/Shanghai")
TYPE_PREFIX = {"food": "05", "hotel": "10"}
PLATFORM_NAMES = {"dianping": "大众点评", "meituan": "美团", "ctrip": "携程"}
PLATFORM_DOMAINS = {"dianping": "dianping.com", "meituan": "meituan.com", "ctrip": "ctrip.com"}
GENERIC_FOOD = {
    "早餐", "午餐", "晚餐", "酒店早餐", "酒店自助早餐", "民宿早餐", "客栈早餐", "住宿早餐",
    "当地小吃", "本地小吃", "当地美食", "本地美食", "当地特色小吃", "本地特色小吃",
    "本地菜午餐", "本地菜晚餐", "当地菜午餐", "当地菜晚餐",
}
GENERIC_HOTEL = {"酒店", "民宿", "客栈", "经济型酒店", "舒适型酒店", "高档型酒店", "豪华型酒店",
                 "当地酒店", "市中心酒店", "待定酒店", "待定住宿"}
DENIED_CODES = {"10001", "10002", "10005", "10007", "10009", "10012", "10013", "10041", "10045", "10046"}
MESSAGES = {
    "generic": "此项是行程安排说明，并非具体门店，不提供门店资料。",
    "insufficient": "门店身份信息不足，暂未核验到具体分店。",
    "unmatched": "未找到与城市、分店及地址或坐标一致的门店。",
    "ambiguous": "存在多个相符门店，暂不展示可能属于其他分店的资料。",
    "available": "门店资料来自高德，仅供出行参考；详情以平台及商家最新信息为准。",
    "no_data": "已核验门店，暂无可获取的参考图片、评分或餐饮特色。",
    "permission_denied": "当前高德权限或配置无法获取完整门店资料，未开通额外服务。",
    "timeout": "门店资料查询超时，可稍后重新展开查看。",
    "unavailable": "门店资料暂不可获取，已核验的平台入口仍可使用。",
}


def city_key(value):
    return normalized(value).removesuffix("市")


def is_generic_merchant(kind, name, city):
    value = normalized(name)
    generic_names = GENERIC_FOOD if kind == "food" else GENERIC_HOTEL
    variants = {value}
    for prefix in {normalized(city), city_key(city), city_key(city) + "市"}:
        if prefix and value.startswith(prefix):
            variants.add(value[len(prefix):])
    return any(v in generic_names or (kind == "food" and re.fullmatch(r"第[0-9零〇一二三四五六七八九十百]+天[早午晚]餐", v)) for v in variants)


def address_key(value, city):
    value = normalized(value)
    # Some upstream addresses include the city, while others start at district.
    for prefix in (city_key(city) + "市", city_key(city)):
        if prefix and value.startswith(prefix):
            return value[len(prefix):]
    return value


def specific_address(value, city):
    value = address_key(value, city)
    return len(value) >= 4 and bool(re.search(r"(?:[0-9]+|[零〇一二三四五六七八九十百千两]+)(?:号|弄|栋|幢|座|楼|层|室)", value))


def coordinates(value):
    try:
        if isinstance(value, dict):
            lng, lat = float(value["longitude"]), float(value["latitude"])
        else:
            lng, lat = map(float, value.split(","))
        if isfinite(lng) and isfinite(lat) and -180 <= lng <= 180 and -90 <= lat <= 90:
            return {"longitude": lng, "latitude": lat}
    except (ValueError, TypeError, KeyError, AttributeError):
        pass
    return None


def within_radius(actual, longitude, latitude):
    if not actual:
        return False
    lng, lat = actual["longitude"], actual["latitude"]
    a = sin(radians(lat - latitude) / 2) ** 2 + cos(radians(latitude)) * cos(radians(lat)) * sin(radians(lng - longitude) / 2) ** 2
    return 6371000 * 2 * asin(sqrt(min(1, a))) <= 500


def safe_http_url(value):
    try:
        parsed = urlsplit(value)
        return (isinstance(value, str) and not any(ord(ch) < 32 for ch in value)
                and parsed.scheme in {"http", "https"} and bool(parsed.hostname)
                and not parsed.username and not parsed.password and parsed.port in {None, 80, 443})
    except (ValueError, TypeError, AttributeError):
        return False


def safe_platform_url(platform, value):
    if platform not in PLATFORM_DOMAINS or not safe_http_url(value):
        return False
    parsed = urlsplit(value)
    domain = PLATFORM_DOMAINS[platform]
    if parsed.hostname != domain and not parsed.hostname.endswith("." + domain):
        return False
    patterns = {
        "dianping": r"/shop/[A-Za-z0-9_-]+/?",
        "meituan": r"/(?:meishi|i/poi|hotel|poi)/[0-9]+(?:\.html)?/?",
        "ctrip": r"/(?:hotels?|html5/hotel/hoteldetail)/[0-9]+\.html/?",
    }
    detail_path = bool(re.fullmatch(patterns[platform], parsed.path))
    if platform == "meituan" and parsed.hostname == "hotel.meituan.com":
        detail_path |= bool(re.fullmatch(r"/[0-9]+/?", parsed.path))
    if not detail_path:
        return False
    # A registry holds public, canonical pages, never login/session share links.
    return not any(re.search(r"token|session|password|authorization|cookie|ticket|openid|redirect|return|callback|^code$|^url$", key, re.I)
                   for key, _ in parse_qsl(parsed.query))


@lru_cache(maxsize=1)
def merchant_registry():
    items = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))["items"]
    enabled = []
    for item in items:
        if item.get("enabled", True) is False:
            continue
        if item["kind"] not in TYPE_PREFIX or not item["name"] or not item["city"]:
            raise ValueError("Invalid merchant identity")
        if not item.get("poi_ids") and not specific_address(item.get("address"), item["city"]) and not coordinates(item.get("location")):
            raise ValueError("Merchant registration requires branch evidence")
        for link in item["links"]:
            date.fromisoformat(link["verified_at"])
            if not safe_platform_url(link["platform"], link["url"]):
                raise ValueError("Invalid merchant platform URL")
            if (item["kind"] == "food" and link["platform"] == "ctrip") or (item["kind"] == "hotel" and link["platform"] == "dianping"):
                raise ValueError("Unsupported platform for merchant kind")
        enabled.append(item)
    return enabled


def registered_links(kind, name, city, address, poi_id, longitude, latitude):
    candidates = []
    for item in merchant_registry():
        if item["kind"] != kind or normalized(item["name"]) != normalized(name) or city_key(item["city"]) != city_key(city):
            continue
        ids = item.get("poi_ids") or []
        if poi_id and ids and poi_id not in ids:
            continue
        if address and address_key(address, city) != address_key(item.get("address"), city):
            continue
        actual = coordinates(item.get("location"))
        if longitude is not None and actual and not within_radius(actual, longitude, latitude):
            continue
        proven = bool(poi_id and poi_id in ids)
        proven |= bool(address and specific_address(address, city) and address_key(address, city) == address_key(item.get("address"), city))
        proven |= bool(longitude is not None and within_radius(actual, longitude, latitude))
        if proven:
            candidates.append(item)
    if len(candidates) != 1:
        return []
    return [{**deepcopy(link), "label": f"在{PLATFORM_NAMES[link['platform']]}查看门店"} for link in candidates[0]["links"]]


def matches_merchant(row, kind, name, city, address, poi_id, longitude, latitude):
    if not isinstance(row, dict) or not row.get("id"):
        return False
    if poi_id and row["id"] != poi_id:
        return False
    if normalized(row.get("name")) != normalized(name) or city_key(row.get("cityname")) != city_key(city):
        return False
    typecode = row.get("typecode")
    if not isinstance(typecode, str) or not any(code.startswith(TYPE_PREFIX[kind]) for code in typecode.split("|")):
        return False
    if address and address_key(address, city) != address_key(row.get("address"), city):
        return False
    if longitude is not None and not within_radius(coordinates(row.get("location")), longitude, latitude):
        return False
    return True


class MerchantLookupError(Exception):
    def __init__(self, status):
        self.status = status


class MerchantInfoService:
    def __init__(self, api_key):
        self.api_key = api_key
        self.cache = OrderedDict()
        self.lock = Lock()

    def request(self, version, path, params):
        if not self.api_key:
            raise MerchantLookupError("permission_denied")
        AmapPlannerClient._wait_for_amap_slot()
        response = httpx.get(f"https://restapi.amap.com/{version}/place/{path}",
                             params={**params, "key": self.api_key}, timeout=8)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "1":
            raise MerchantLookupError("permission_denied" if str(data.get("infocode")) in DENIED_CODES else "unavailable")
        rows = data.get("pois")
        return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []

    def lookup(self, result, kind, name, city, address, poi_id, longitude, latitude):
        if poi_id:
            rows = self.request("v3", "detail", {"id": poi_id, "extensions": "base"})
        else:
            rows = self.request("v3", "text", {"keywords": name, "city": city, "citylimit": "true",
                                                "types": TYPE_PREFIX[kind] + "0000", "extensions": "base", "offset": 25, "page": 1})
        found = {r["id"]: r for r in rows if matches_merchant(r, kind, name, city, address, poi_id, longitude, latitude)}
        if len(found) != 1:
            result["match_status"] = "ambiguous" if len(found) > 1 else "unmatched"
            return
        row = next(iter(found.values()))
        resolved_id = row["id"]
        result.update(match_status="matched", place={"poi_id": resolved_id, "name": row["name"],
            "city": row["cityname"], "address": row.get("address") if isinstance(row.get("address"), str) else "",
            "location": coordinates(row.get("location"))}, source={"name": "高德地图（参考资料）",
            "url": "https://uri.amap.com/marker?" + urlencode({"poiid": resolved_id, "name": row["name"], "src": "trip-planner"}),
            "queried_at": result["queried_at"]})
        # Keep basic identity/map even if optional POI 2.0 fields are not authorized.
        rows = self.request("v5", "detail", {"id": resolved_id, "show_fields": "business,photos"})
        if not rows:
            return
        details = [r for r in rows if matches_merchant(r, kind, name, city, address, resolved_id, longitude, latitude)]
        if len(details) != 1:
            result.update(match_status="unmatched", place=None, source=None)
            return
        row = details[0]
        business = row.get("business") if isinstance(row.get("business"), dict) else {}
        rating = business.get("rating")
        if isinstance(rating, (str, int, float)) and not isinstance(rating, bool):
            try:
                if isfinite(float(rating)) and 0 < float(rating) <= 5:
                    result["rating"] = str(rating).strip()
            except ValueError:
                pass
        tag = business.get("tag")
        if kind == "food" and isinstance(tag, str):
            result["food_tags"] = list(dict.fromkeys(t.strip() for t in re.split(r"[;,；，|]", tag) if t.strip()))[:8]
        photos = row.get("photos") if isinstance(row.get("photos"), list) else []
        seen = set()
        for photo in photos:
            if not isinstance(photo, dict) or not safe_http_url(photo.get("url")) or photo["url"] in seen:
                continue
            title = photo.get("title")
            result["photos"].append({"url": photo["url"], "title": title.strip() if isinstance(title, str) and title.strip() else "门店参考图"})
            seen.add(photo["url"])
            if len(result["photos"]) == 3:
                break
        if result["photos"] or result["rating"] or result["food_tags"]:
            result["data_status"] = "available"

    def resolve(self, kind, name, city, address="", poi_id="", longitude=None, latitude=None):
        if kind not in TYPE_PREFIX:
            raise ValueError("Invalid merchant kind")
        if (longitude is None) != (latitude is None) or (longitude is not None and not coordinates({"longitude": longitude, "latitude": latitude})):
            raise ValueError("Invalid merchant coordinates")
        started = monotonic()
        key = (kind, normalized(name), city_key(city), address_key(address, city), poi_id, longitude, latitude)
        cached = False
        with self.lock:
            item = self.cache.get(key)
            if item and item[0] > monotonic():
                result = deepcopy(item[1])
                self.cache.move_to_end(key)
                cached = True
        if not cached:
            result = {"match_status": "insufficient", "data_status": "no_data", "message": "", "place": None,
                      "photos": [], "rating": None, "food_tags": [], "source": None, "links": [],
                      "queried_at": datetime.now(CHINA).isoformat()}
            if is_generic_merchant(kind, name, city):
                result["match_status"] = "generic"
            elif name.strip() and city.strip() and (poi_id or longitude is not None or specific_address(address, city)):
                try:
                    self.lookup(result, kind, name, city, address, poi_id, longitude, latitude)
                except MerchantLookupError as exc:
                    result["data_status"] = exc.status
                except httpx.TimeoutException:
                    result["data_status"] = "timeout"
                except Exception as exc:
                    # Never log exception text/HTTP request URLs, which may contain the key.
                    logger.warning("poi.merchant_info_failed", extra={"error_type": type(exc).__name__})
                    result["data_status"] = "unavailable"
            if result["match_status"] not in {"generic", "unmatched", "ambiguous"}:
                resolved = result["place"]
                try:
                    result["links"] = registered_links(kind, name, city, address, resolved["poi_id"] if resolved else poi_id, longitude, latitude)
                except Exception as exc:
                    logger.warning("poi.merchant_registry_failed", extra={"error_type": type(exc).__name__})
            message_key = result["data_status"] if result["data_status"] not in {"available", "no_data"} else (
                result["data_status"] if result["match_status"] == "matched" else result["match_status"])
            result["message"] = MESSAGES[message_key]
            # Do not pin transient permission/network failures for fifteen minutes.
            if result["data_status"] in {"available", "no_data"}:
                with self.lock:
                    self.cache[key] = (monotonic() + 900, deepcopy(result))
                    self.cache.move_to_end(key)
                    while len(self.cache) > 512:
                        self.cache.popitem(last=False)
        logger.info("poi.merchant_info_resolved", extra={"merchant_kind": kind, "match_status": result["match_status"],
                    "data_status": result["data_status"], "cache_hit": cached, "elapsed_ms": round((monotonic() - started) * 1000)})
        return result


@lru_cache(maxsize=1)
def get_merchant_info_service():
    return MerchantInfoService(get_settings().secret_value("amap_api_key"))
