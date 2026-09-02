"""Travel-planning API routes backed by the compiled LangGraph workflow."""

from fastapi import APIRouter, HTTPException

from ...models.schemas import TripPlanResponse, TripRequest
from ...services.trip_planner_service import get_trip_planner_service


router = APIRouter(prefix="/trip", tags=["旅行规划"])


@router.post("/plan", response_model=TripPlanResponse, summary="生成旅行计划")
async def plan_trip(request: TripRequest) -> TripPlanResponse:
    try:
        result = await get_trip_planner_service().plan_trip(request)
        return TripPlanResponse(
            success=True,
            message=result["generation_message"],
            data=result["trip_plan"],
            metadata=result.get("model_metadata", {}),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成旅行计划失败: {exc}") from exc


@router.get("/health", summary="检查规划图和模型配置")
async def health_check() -> dict:
    try:
        return get_trip_planner_service().describe()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"服务不可用: {exc}") from exc
