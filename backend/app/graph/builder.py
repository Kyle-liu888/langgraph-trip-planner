"""Compile the LangGraph planner workflow."""

from langgraph.graph import END, START, StateGraph

from .nodes import (
    build_prompt,
    collect_context,
    create_fallback,
    generate_candidate,
    route_after_validation,
    select_best_candidate,
    validate_candidate,
)
from .runtime import PlannerRuntime
from .state import PlannerInput, PlannerOutput, PlannerState


def build_planner_graph():
    builder = StateGraph(
        PlannerState,
        input_schema=PlannerInput,
        output_schema=PlannerOutput,
        context_schema=PlannerRuntime,
    )
    builder.add_node("collect_context", collect_context)
    builder.add_node("build_prompt", build_prompt)
    builder.add_node("generate_candidate", generate_candidate)
    builder.add_node("validate_candidate", validate_candidate)
    builder.add_node("select_best_candidate", select_best_candidate)
    builder.add_node("create_fallback", create_fallback)

    builder.add_edge(START, "collect_context")
    builder.add_edge("collect_context", "build_prompt")
    builder.add_edge("build_prompt", "generate_candidate")
    builder.add_edge("generate_candidate", "validate_candidate")
    builder.add_conditional_edges(
        "validate_candidate",
        route_after_validation,
        {
            "retry": "generate_candidate",
            "select": "select_best_candidate",
            "fallback": "create_fallback",
        },
    )
    builder.add_edge("select_best_candidate", END)
    builder.add_edge("create_fallback", END)
    return builder.compile()
