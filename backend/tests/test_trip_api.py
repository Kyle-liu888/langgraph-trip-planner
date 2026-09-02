import asyncio
from unittest.mock import patch

from app.api.routes.trip import health_check, plan_trip
from app.models.schemas import BudgetConstraint, PartyInfo, TripRequest
from app.planner.output import create_fallback_plan


def make_request() -> TripRequest:
    return TripRequest(
        city="杭州",
        start_date="2026-10-01",
        end_date="2026-10-01",
        travel_days=1,
        transportation="公共交通",
        accommodation="舒适型酒店",
        party=PartyInfo(adults=1, children=0, elders=0, total=1),
        budget_constraint=BudgetConstraint(amount=800, strictness="soft"),
    )


class FakeTripPlannerService:
    async def plan_trip(self, request: TripRequest):
        return {
            "trip_plan": create_fallback_plan(request),
            "generation_status": "llm_success",
            "generation_message": "fake:model 生成成功",
            "model_metadata": {"provider": "fake", "model": "model"},
        }

    def describe(self):
        return {"status": "healthy", "service": "langgraph-trip-planner"}


def test_plan_route_preserves_response_contract_and_metadata() -> None:
    service = FakeTripPlannerService()
    with patch("app.api.routes.trip.get_trip_planner_service", return_value=service):
        response = asyncio.run(plan_trip(make_request()))

    assert response.success is True
    assert response.data is not None
    assert response.data.city == "杭州"
    assert response.metadata == {"provider": "fake", "model": "model"}


def test_trip_health_uses_service_description() -> None:
    service = FakeTripPlannerService()
    with patch("app.api.routes.trip.get_trip_planner_service", return_value=service):
        response = asyncio.run(health_check())

    assert response["status"] == "healthy"
