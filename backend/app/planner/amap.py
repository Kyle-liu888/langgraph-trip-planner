"""高德 API 调用、缓存和 POI 搜索封装。"""

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from ..observability import logger

from .pois import dedupe_pois, filter_pois, normalize_pois, rank_pois


AMAP_BASE_URL = "https://restapi.amap.com/v3"
AMAP_HTTP_TIMEOUT = int(os.getenv("AMAP_HTTP_TIMEOUT", "30"))
AMAP_SEARCH_OFFSET = int(os.getenv("AMAP_SEARCH_OFFSET", "20"))
PLANNER_CONTEXT_PER_KEYWORD_LIMIT = int(os.getenv("PLANNER_CONTEXT_PER_KEYWORD_LIMIT", "5"))
PLANNER_CONTEXT_CACHE_DIR = Path(
    os.getenv("PLANNER_CONTEXT_CACHE_DIR", ".cache/planner_context")
)
PLANNER_CONTEXT_CACHE_TTL_SECONDS = int(
    os.getenv("PLANNER_CONTEXT_CACHE_TTL_SECONDS", str(60 * 24 * 60 * 60))
)
PLANNER_CONTEXT_AMAP_CACHE_TTL_SECONDS = int(
    os.getenv("PLANNER_CONTEXT_AMAP_CACHE_TTL_SECONDS", str(PLANNER_CONTEXT_CACHE_TTL_SECONDS))
)
PLANNER_CONTEXT_CLASSIC_CACHE_TTL_SECONDS = int(
    os.getenv("PLANNER_CONTEXT_CLASSIC_CACHE_TTL_SECONDS", str(PLANNER_CONTEXT_CACHE_TTL_SECONDS))
)
PLANNER_CONTEXT_CACHE_VERBOSE = os.getenv("PLANNER_CONTEXT_CACHE_VERBOSE", "0") == "1"
AMAP_QPS_LIMIT = float(os.getenv("AMAP_QPS_LIMIT", "3"))
AMAP_MIN_INTERVAL_SECONDS = 1.0 / AMAP_QPS_LIMIT if AMAP_QPS_LIMIT > 0 else 0.0

_AMAP_RATE_LIMIT_LOCK = threading.Lock()
_AMAP_LAST_REQUEST_AT = 0.0


def set_amap_qps_limit(qps_limit: float) -> None:
    """Override the process-local Amap HTTP QPS limit at runtime."""
    if qps_limit < 0:
        raise ValueError("AMAP QPS limit must be >= 0")

    global AMAP_QPS_LIMIT, AMAP_MIN_INTERVAL_SECONDS, _AMAP_LAST_REQUEST_AT
    AMAP_QPS_LIMIT = float(qps_limit)
    AMAP_MIN_INTERVAL_SECONDS = 1.0 / AMAP_QPS_LIMIT if AMAP_QPS_LIMIT > 0 else 0.0
    with _AMAP_RATE_LIMIT_LOCK:
        _AMAP_LAST_REQUEST_AT = 0.0


class AmapPlannerClient:
    """面向 PlannerContext 的高德查询客户端。"""

    def __init__(self, api_key: str, cache_dir: Path = PLANNER_CONTEXT_CACHE_DIR):
        self.api_key = api_key
        self.cache_dir = self._resolve_cache_dir(cache_dir)

    def get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """调用高德HTTP API，并在入口统一做缓存和限速。"""
        if not self.api_key:
            raise ValueError("AMAP_API_KEY未配置")

        query_params = {key: value for key, value in params.items() if value not in (None, "")}
        cache_path = self._amap_cache_path(path, query_params)
        cached = self._read_cache(
            cache_path,
            value_key="data",
            ttl_seconds=PLANNER_CONTEXT_AMAP_CACHE_TTL_SECONDS,
        )
        if cached is not None:
            if PLANNER_CONTEXT_CACHE_VERBOSE:
                logger.debug("amap.cache_hit", extra={"endpoint": path})
            return cached

        request_params = {**query_params, "key": self.api_key}
        last_exc: Optional[Exception] = None
        for attempt in range(3):
            try:
                self._wait_for_amap_slot()
                response = httpx.get(f"{AMAP_BASE_URL}{path}", params=request_params, timeout=AMAP_HTTP_TIMEOUT)
                response.raise_for_status()
                data = response.json()
                if data.get("status") == "0":
                    raise RuntimeError(f"高德API错误: {data.get('info')} ({data.get('infocode')})")
                self._write_cache(
                    cache_path,
                    data,
                    value_key="data",
                    ttl_seconds=PLANNER_CONTEXT_AMAP_CACHE_TTL_SECONDS,
                    label="amap",
                )
                return data
            except Exception as exc:
                last_exc = exc
                logger.warning("amap.retry", extra={"endpoint": path, "attempt": attempt + 1, "error_type": type(exc).__name__})
                time.sleep(0.5 + attempt)
        raise RuntimeError(f"高德API请求失败: {last_exc}") from last_exc

    def search_keywords(
        self,
        city: str,
        keywords: List[str],
        source_role: str,
        limit: int,
        require_location: bool = True,
        source_bucket: str = "",
    ) -> List[Dict[str, Any]]:
        """按多个关键词搜索POI并去重。"""
        rows = []
        for keyword in keywords:
            raw = self.get(
                "/place/text",
                {
                    "keywords": keyword,
                    "city": city,
                    "citylimit": "true",
                    "extensions": "all",
                    "offset": AMAP_SEARCH_OFFSET,
                    "page": 1,
                },
            )
            normalized = normalize_pois(raw, keyword, source_role, require_location, source_bucket)
            normalized = filter_pois(normalized, source_role)
            normalized = rank_pois(normalized, source_role)
            rows.extend(normalized[:PLANNER_CONTEXT_PER_KEYWORD_LIMIT])
        rows = dedupe_pois(rows)
        rows = rank_pois(rows, source_role)
        return rows[:limit]

    def search_classic_pois(self, city: str, keywords: List[str], limit: int) -> List[Dict[str, Any]]:
        """查询城市经典景点；这部分和用户无关，适合长 TTL 本地缓存。"""
        cache_path = self._classic_cache_path(city, keywords)
        cached = self._read_cache(
            cache_path,
            value_key="rows",
            ttl_seconds=PLANNER_CONTEXT_CLASSIC_CACHE_TTL_SECONDS,
        )
        if cached is not None:
            # print(f"  - classic_pois缓存命中: {city} ({len(cached)}条)")
            return cached

        rows = self.search_keywords(
            city,
            keywords,
            source_role="scenic",
            limit=limit,
            source_bucket="classic",
        )
        self._write_cache(
            cache_path,
            rows,
            value_key="rows",
            ttl_seconds=PLANNER_CONTEXT_CLASSIC_CACHE_TTL_SECONDS,
            label="classic_pois",
        )
        return rows

    def _resolve_cache_dir(self, path: Path) -> Path:
        """把相对缓存目录解析到项目根目录附近，避免依赖启动目录。"""
        if path.is_absolute():
            return path
        # backend/app/planner/amap.py -> project root
        project_root = Path(__file__).resolve().parents[3]
        return project_root / path

    def _classic_cache_path(self, city: str, keywords: List[str]) -> Path:
        """生成城市经典候选缓存路径。"""
        safe_city = "".join(ch for ch in city if ch.isalnum() or ch in ("-", "_")) or "unknown"
        keyword_sig = "_".join(keywords)
        # 关键词基本固定，hash 用内置 hash 不稳定；这里用长度较短的手写签名足够。
        suffix = str(abs(sum(ord(ch) for ch in keyword_sig)))
        return self.cache_dir / "classic_pois" / f"{safe_city}_{suffix}.json"

    def _amap_cache_path(self, path: str, params: Dict[str, Any]) -> Path:
        """生成高德原始HTTP响应缓存路径，不把API key写进缓存签名。"""
        safe_path = path.strip("/").replace("/", "_") or "root"
        payload = {
            "path": path,
            "params": {key: str(params[key]) for key in sorted(params)},
        }
        digest = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()[:24]
        label = self._cache_label(params) or "query"
        return self.cache_dir / "amap_api" / safe_path / f"{label}_{digest}.json"

    def _cache_label(self, params: Dict[str, Any]) -> str:
        """生成便于人工查看的缓存文件名前缀。"""
        parts = []
        for key in ("city", "keywords", "extensions"):
            value = str(params.get(key) or "").strip()
            if value:
                parts.append(self._safe_cache_text(value)[:24])
        return "_".join(parts)

    def _safe_cache_text(self, value: str) -> str:
        """把城市/关键词压成适合文件名的短文本。"""
        safe = "".join(ch for ch in value if ch.isalnum() or ch in ("-", "_"))
        return safe or "query"

    @staticmethod
    def _wait_for_amap_slot() -> None:
        """进程内限速，避免并发cache miss时超过高德QPS限制。"""
        if AMAP_MIN_INTERVAL_SECONDS <= 0:
            return

        global _AMAP_LAST_REQUEST_AT
        with _AMAP_RATE_LIMIT_LOCK:
            now = time.monotonic()
            wait_seconds = AMAP_MIN_INTERVAL_SECONDS - (now - _AMAP_LAST_REQUEST_AT)
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            _AMAP_LAST_REQUEST_AT = time.monotonic()

    def _read_cache(
        self,
        path: Path,
        value_key: str = "rows",
        ttl_seconds: int = PLANNER_CONTEXT_CACHE_TTL_SECONDS,
    ) -> Optional[Any]:
        """读取未过期缓存。"""
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            created_at = float(data.get("created_at", 0))
            if time.time() - created_at > ttl_seconds:
                return None
            return data.get(value_key)
        except Exception:
            return None

    def _write_cache(
        self,
        path: Path,
        value: Any,
        value_key: str = "rows",
        ttl_seconds: int = PLANNER_CONTEXT_CACHE_TTL_SECONDS,
        label: str = "cache",
    ) -> None:
        """写入缓存；失败不影响主流程。"""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "created_at": time.time(),
                "ttl_seconds": ttl_seconds,
                value_key: value,
            }
            tmp_path = path.with_suffix(f".tmp.{os.getpid()}.{threading.get_ident()}")
            tmp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            tmp_path.replace(path)
        except Exception as exc:
            logger.warning("cache.write_failed", extra={"cache": label, "error_type": type(exc).__name__})
