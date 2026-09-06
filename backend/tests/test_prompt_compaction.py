import copy

from app.planner.compact import compact_for_planner
from app.graph.query import build_planner_query
from test_planner_graph import make_request, StubContextBuilder


def test_deduplicate_attractions_without_losing_price_variants_or_food_constraints():
    poi = {"name": "公园", "location": {"longitude": 116, "latitude": 39}, "ticket_price_hint": 0,
           "source_bucket": "classic", "source_keyword": "风景", "cost": "无"}
    context = {"tool_snapshot": {
        "classic_pois": [poi],
        "scenic_pois": [{**poi, "source_bucket": "scenic", "source_keyword": "公园"},
                        {**poi, "ticket_price_hint": 20}],
        "food_pois": [{"name": "餐厅", "meal_cost_hint": 50, "avoid_risk_keywords": ["花生"],
                       "meal_roles": ["lunch", "dinner"], "diet_tags": ["素食"]}]
    }}
    before = copy.deepcopy(context)
    result = compact_for_planner(context)["tool_snapshot"]
    assert context == before
    assert len(result["classic_pois"]) == 1 and len(result["scenic_pois"]) == 1
    assert result["classic_pois"][0]["ticket_price_hint"] == 0
    assert result["scenic_pois"][0]["ticket_price_hint"] == 20
    assert result["candidate_counts"]["scenic_pois"] == 1
    assert result["food_pois"][0]["avoid_risk_keywords"] == ["花生"]
    assert result["food_pois"][0]["meal_roles"] == ["lunch", "dinner"]


def test_user_extra_requirements_remain_in_compact_prompt():
    request = make_request().model_copy(update={"free_text_input": "不要安排爬山，必须避开花生"})
    context = StubContextBuilder().collect(request)
    query = build_planner_query(StubContextBuilder(), request, context)
    assert request.free_text_input in query
