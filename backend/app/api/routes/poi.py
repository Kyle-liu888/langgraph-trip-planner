"""POI相关API路由"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from ...config import get_settings
from ...observability import logger
from ...planner.amap import AmapPlannerClient
from ...services.amap_service import get_amap_service
from ...services.poi_photo_service import get_poi_photo_service

router = APIRouter(prefix="/poi", tags=["POI"])
SEARCH_SOURCE_ROLES = {"food", "scenic", "hotel"}


class POIDetailResponse(BaseModel):
    """POI详情响应"""
    success: bool
    message: str
    data: Optional[dict] = None


@router.get(
    "/detail/{poi_id}",
    response_model=POIDetailResponse,
    summary="获取POI详情",
    description="根据POI ID获取详细信息,包括图片"
)
def get_poi_detail(poi_id: str):
    """
    获取POI详情

    Args:
        poi_id: POI ID

    Returns:
        POI详情响应
    """
    try:
        amap_service = get_amap_service()

        # 调用高德地图POI详情API
        result = amap_service.get_poi_detail(poi_id)

        return POIDetailResponse(
            success=True,
            message="获取POI详情成功",
            data=result
        )

    except Exception as e:
        logger.exception("poi.detail_failed")
        raise HTTPException(
            status_code=500,
            detail={"code": "POI_FAILED", "message": "获取地点详情失败，请稍后重试"}
        )


@router.get(
    "/search",
    summary="搜索POI",
    description="根据关键词搜索POI"
)
def search_poi(
    keywords: str,
    city: str = "北京",
    source_role: str = Query(default="food", description="POI类型: food/scenic/hotel")
):
    """
    搜索POI

    Args:
        keywords: 搜索关键词
        city: 城市名称

    Returns:
        搜索结果
    """
    try:
        role = source_role if source_role in SEARCH_SOURCE_ROLES else "food"
        settings = get_settings()
        amap_key = settings.secret_value("amap_api_key")
        if not amap_key:
            raise ValueError("高德地图API Key未配置")

        amap_client = AmapPlannerClient(amap_key)
        result = amap_client.search_keywords(
            city=city,
            keywords=[keywords],
            source_role=role,
            limit=5,
            require_location=True,
            source_bucket="frontend_search",
        )

        return {
            "success": True,
            "message": "搜索成功",
            "data": result
        }

    except Exception as e:
        logger.exception("poi.search_failed")
        raise HTTPException(
            status_code=500,
            detail={"code": "POI_FAILED", "message": "地点搜索失败，请稍后重试"}
        )


@router.get(
    "/photo",
    summary="获取景点图片",
    description="获取经城市、名称及坐标核对的高德地点照片；无可靠匹配时不配图"
)
def get_attraction_photo(
    name: str = Query(min_length=1, max_length=120),
    city: str = Query(default="", max_length=80),
    poi_id: str = Query(default="", max_length=40, pattern=r"^[A-Za-z0-9_-]*$"),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    latitude: float | None = Query(default=None, ge=-90, le=90),
):
    try:
        data = get_poi_photo_service().resolve(name, city, poi_id, longitude, latitude)
        logger.info("poi.photo_resolved", extra={"photo_status": data["status"]})
        return {"success": True, "data": {"name": name, **data}}
    except Exception as exc:
        # Never log exception text: HTTP errors can contain the API key in the URL.
        logger.warning("poi.photo_unavailable", extra={"error_type": type(exc).__name__})
        return {"success": False, "data": {"name": name, "photo_url": None, "source": None, "status": "unavailable", "poi_id": None}}
