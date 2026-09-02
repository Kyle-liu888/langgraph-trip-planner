"""POI相关API路由"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from ...config import get_settings
from ...planner.amap import AmapPlannerClient
from ...services.amap_service import get_amap_service
from ...services.unsplash_service import get_unsplash_service

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
async def get_poi_detail(poi_id: str):
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
        print(f"[ERROR] 获取POI详情失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取POI详情失败: {str(e)}"
        )


@router.get(
    "/search",
    summary="搜索POI",
    description="根据关键词搜索POI"
)
async def search_poi(
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
        print(f"[ERROR] 搜索POI失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"搜索POI失败: {str(e)}"
        )


@router.get(
    "/photo",
    summary="获取景点图片",
    description="根据景点名称从Unsplash获取图片"
)
async def get_attraction_photo(name: str):
    """
    获取景点图片

    Args:
        name: 景点名称

    Returns:
        图片URL
    """
    try:
        unsplash_service = get_unsplash_service()

        # 搜索景点图片
        photo_url = unsplash_service.get_photo_url(f"{name} China landmark")

        if not photo_url:
            # 如果没找到,尝试只用景点名称搜索
            photo_url = unsplash_service.get_photo_url(name)

        return {
            "success": True,
            "message": "获取图片成功",
            "data": {
                "name": name,
                "photo_url": photo_url
            }
        }

    except Exception as e:
        print(f"[ERROR] 获取景点图片失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取景点图片失败: {str(e)}"
        )
