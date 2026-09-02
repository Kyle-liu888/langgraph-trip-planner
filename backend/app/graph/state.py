"""Typed state contracts for the planner graph."""

from __future__ import annotations

from typing import Any
from typing_extensions import NotRequired, TypedDict

from ..models.schemas import TripPlan, TripRequest


class PlannerInput(TypedDict):
    request: TripRequest


class PlannerOutput(TypedDict):
    trip_plan: TripPlan
    generation_status: str
    generation_message: str
    model_metadata: dict[str, Any]


class PlannerState(PlannerInput, total=False):
    planner_context: dict[str, Any]
    planner_query: str
    attempt: int
    candidate: NotRequired[TripPlan | None]
    candidates: list[tuple[int, TripPlan]]
    last_error: str
    structured_strategy: str
    model_metadata: dict[str, Any]
    trip_plan: TripPlan
    generation_status: str
    generation_message: str
