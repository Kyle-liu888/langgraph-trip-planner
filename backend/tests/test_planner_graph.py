import asyncio
import json

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.config import Settings
from app.graph import PlannerRuntime, build_planner_graph
from app.llm.config import ModelConfig
from app.models.schemas import BudgetConstraint, PartyInfo, TripRequest
from app.planner.policy import build_empty_context


class StubContextBuilder:
    def collect(self, request: TripRequest):
        return build_empty_context(request)

    def compact_for_planner(self, context):
        return context


def make_request() -> TripRequest:
    return TripRequest(
        city="北京",
        start_date="2026-10-01",
        end_date="2026-10-01",
        travel_days=1,
        transportation="公共交通",
        accommodation="经济型酒店",
        preferences=["历史文化"],
        party=PartyInfo(adults=1, children=0, elders=0, total=1),
        budget_constraint=BudgetConstraint(amount=500, strictness="soft"),
    )


def valid_plan_json() -> str:
    return json.dumps(
        {
            "city": "北京",
            "start_date": "2026-10-01",
            "end_date": "2026-10-01",
            "days": [
                {
                    "date": "2026-10-01",
                    "day_index": 0,
                    "description": "历史文化一日游",
                    "transportation": "公共交通",
                    "accommodation": "经济型酒店",
                    "hotel": None,
                    "attractions": [
                        {
                            "name": "故宫博物院",
                            "address": "北京市东城区景山前街4号",
                            "location": {"longitude": 116.397, "latitude": 39.916},
                            "visit_duration": 180,
                            "description": "参观古代宫殿建筑群",
                            "ticket_price": 60,
                        }
                    ],
                    "meals": [
                        {"type": "breakfast", "name": "酒店早餐", "estimated_cost": 20},
                        {"type": "lunch", "name": "四季民福", "estimated_cost": 80},
                        {"type": "dinner", "name": "东来顺", "estimated_cost": 100},
                    ],
                }
            ],
            "weather_info": [
                {
                    "date": "2026-10-01",
                    "day_weather": "远期天气暂无准确预报",
                    "night_weather": "远期天气暂无准确预报",
                    "day_temp": "未知",
                    "night_temp": "未知",
                }
            ],
            "overall_suggestions": "提前预约景点。",
            "budget": {
                "total_attractions": 60,
                "total_hotels": 0,
                "total_meals": 200,
                "total_transportation": 40,
                "total": 300,
            },
        },
        ensure_ascii=False,
    )


def make_runtime(responses: list[str], max_attempts: int = 2) -> PlannerRuntime:
    settings = Settings(
        LLM_PROVIDER="fake",
        LLM_MODEL="fake-chat",
        PLANNER_MAX_ATTEMPTS=max_attempts,
        PLANNER_ENABLE_RERANK=False,
    )
    return PlannerRuntime(
        model=FakeListChatModel(responses=responses),
        model_config=ModelConfig(
            provider="fake",
            model="fake-chat",
            structured_output_mode="prompt",
        ),
        context_builder=StubContextBuilder(),
        settings=settings,
    )


def test_graph_retries_invalid_json_then_returns_valid_plan() -> None:
    graph = build_planner_graph()
    runtime = make_runtime(["not-json", valid_plan_json()])

    result = asyncio.run(graph.ainvoke({"request": make_request()}, context=runtime))

    assert result["generation_status"] == "llm_success"
    assert result["trip_plan"]["city"] == "北京"
    assert result["model_metadata"]["attempts"] == 2
    assert result["model_metadata"]["structured_strategy"] == "prompt"


def test_graph_returns_deterministic_fallback_after_attempt_limit() -> None:
    graph = build_planner_graph()
    runtime = make_runtime(["not-json", "still-not-json"])

    result = asyncio.run(graph.ainvoke({"request": make_request()}, context=runtime))

    assert result["generation_status"] == "fallback_success"
    assert result["trip_plan"]["city"] == "北京"
    assert len(result["trip_plan"]["days"]) == 1
