"""Application service that owns the compiled graph and its dependencies."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from ..config import Settings, get_settings
from ..graph import PlannerRuntime, build_planner_graph
from ..llm import ModelConfig, create_chat_model
from ..models.schemas import TripRequest
from ..planner.context import PlannerContextBuilder


class TripPlannerService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.model_config = ModelConfig.from_settings(self.settings)
        self.model = create_chat_model(self.model_config)
        self.context_builder = PlannerContextBuilder(
            self.settings.secret_value("amap_api_key")
        )
        self.graph = build_planner_graph()
        self.runtime = PlannerRuntime(
            model=self.model,
            model_config=self.model_config,
            context_builder=self.context_builder,
            settings=self.settings,
        )

    async def plan_trip(self, request: TripRequest) -> dict[str, Any]:
        return await self.graph.ainvoke({"request": request}, context=self.runtime)

    def describe(self) -> dict[str, Any]:
        return {
            "status": "healthy",
            "service": "langgraph-trip-planner",
            "provider": self.model_config.provider,
            "model": self.model_config.model,
            "structured_output_mode": self.model_config.structured_output_mode,
            "graph_nodes": list(self.graph.nodes),
        }


@lru_cache(maxsize=1)
def get_trip_planner_service() -> TripPlannerService:
    return TripPlannerService()
