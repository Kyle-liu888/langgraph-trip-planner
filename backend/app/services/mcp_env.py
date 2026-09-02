"""Helpers for MCP server subprocess environments."""

import os
from pathlib import Path
from typing import Dict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def build_amap_mcp_env(amap_api_key: str) -> Dict[str, str]:
    """Build the explicit environment passed to the amap MCP stdio server."""
    env = {
        "AMAP_MAPS_API_KEY": amap_api_key,
        "UV_CACHE_DIR": os.getenv("UV_CACHE_DIR", str(PROJECT_ROOT / ".uv-cache")),
    }
    for key in ("http_proxy", "https_proxy", "all_proxy", "NO_PROXY", "no_proxy"):
        value = os.getenv(key)
        if value:
            env[key] = value
    return env
