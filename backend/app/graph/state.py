"""Typed state contracts for the planner graph."""

from __future__ import annotations

from typing import Any
from typing_extensions import NotRequired, TypedDict



class PlannerInput(TypedDict):
    request: dict[str, Any]


class PlannerOutput(TypedDict):
    trip_plan: dict[str, Any]
    generation_status: str
    generation_message: str
    model_metadata: dict[str, Any]


class PlannerState(PlannerInput, total=False):
    planner_context: dict[str, Any]
    planner_query: str
    attempt: int
    candidate: NotRequired[dict[str, Any] | None]
    candidates: list[dict[str, Any]]
    last_error: str
    structured_strategy: str
    model_metadata: dict[str, Any]
    trip_plan: dict[str, Any]
    generation_status: str
    generation_message: str
