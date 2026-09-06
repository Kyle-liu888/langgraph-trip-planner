"""Resolve photos from verified Amap places, never generic stock-image searches."""
from collections import OrderedDict
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt
from threading import Lock
from time import monotonic
from urllib.parse import urlsplit

import httpx

from ..config import get_settings
from ..planner.amap import AMAP_BASE_URL, AmapPlannerClient


def normalized(value):
    return "".join(str(value or "").split()).replace("（", "(").replace("）", ")")


def matches(row, name, city, longitude, latitude):
    if normalized(row.get("name")) != normalized(name):
        return False
    if normalized(row.get("cityname")).removesuffix("市") != normalized(city).removesuffix("市"):
        return False
    if longitude is not None and latitude is not None:
        try:
            lng, lat = map(float, row["location"].split(","))
            if not (-180 <= lng <= 180 and -90 <= lat <= 90):
                return False
            a = sin(radians(lat - latitude) / 2) ** 2 + cos(radians(latitude)) * cos(radians(lat)) * sin(radians(lng - longitude) / 2) ** 2
            if 6371000 * 2 * asin(sqrt(min(1, a))) > 500:
                return False
        except (KeyError, TypeError, ValueError):
            return False
    return True


class PoiPhotoService:
    def __init__(self, key):
        self.key = key
        self.cache = OrderedDict()
        self.lock = Lock()

    def request(self, path, params):
        if not self.key:
            raise ValueError("AMAP_API_KEY not configured")
        AmapPlannerClient._wait_for_amap_slot()
        # Photos are optional: short deadline, no retries, no model calls.
        response = httpx.get(f"{AMAP_BASE_URL}{path}", params={**params, "key": self.key}, timeout=8)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "1":
            raise ValueError("Amap photo lookup unavailable")
        return data.get("pois") or []

    def resolve(self, name, city, poi_id="", longitude=None, latitude=None):
        key = (name, city, poi_id, longitude, latitude)
        with self.lock:
            cached = self.cache.get(key)
            if cached and cached[0] > monotonic():
                self.cache.move_to_end(key)
                return dict(cached[1])
        result = {"photo_url": None, "source": None, "status": "unmatched", "poi_id": None}
        if not city.strip() or (not poi_id and (longitude is None or latitude is None)):
            return result
        if poi_id:
            rows = self.request("/place/detail", {"id": poi_id, "extensions": "all"})
            rows = [r for r in rows if r.get("id") == poi_id]
        else:
            rows = self.request("/place/text", {"keywords": name, "city": city, "citylimit": "true", "extensions": "all", "offset": 10, "page": 1})
        candidates = {r.get("id"): r for r in rows if r.get("id") and matches(r, name, city, longitude, latitude)}
        if len(candidates) == 1:
            row = next(iter(candidates.values()))
            result.update(status="no_photo", poi_id=row["id"])
            for photo in row.get("photos") or []:
                url = photo.get("url") if isinstance(photo, dict) else None
                if not isinstance(url, str):
                    continue
                try:
                    parsed = urlsplit(url)
                    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
                        continue
                except ValueError:
                    continue
                result.update(photo_url=url, source="amap", status="available")
                break
        with self.lock:
            self.cache[key] = (monotonic() + 300, dict(result))
            self.cache.move_to_end(key)
            while len(self.cache) > 512:
                self.cache.popitem(last=False)
        return result


@lru_cache(maxsize=1)
def get_poi_photo_service():
    return PoiPhotoService(get_settings().secret_value("amap_api_key"))
