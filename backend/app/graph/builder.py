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
from ..observability import instrument_node


def build_planner_graph(checkpointer=None):
    builder = StateGraph(
        PlannerState,
        input_schema=PlannerInput,
        output_schema=PlannerOutput,
        context_schema=PlannerRuntime,
    )
    for node in (collect_context, build_prompt, generate_candidate, validate_candidate,
                 select_best_candidate, create_fallback):
        builder.add_node(node.__name__, instrument_node(node))

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
    return builder.compile(checkpointer=checkpointer)
