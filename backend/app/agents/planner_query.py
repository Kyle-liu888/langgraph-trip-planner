"""Planner 输入构造和输出 token 预算。"""

import json
import os
from typing import Any, Dict

from ..models.schemas import TripRequest


PLANNER_OUTPUT_BASE_TOKENS = int(os.getenv("PLANNER_OUTPUT_BASE_TOKENS", "3000"))
PLANNER_OUTPUT_TOKENS_PER_DAY = int(os.getenv("PLANNER_OUTPUT_TOKENS_PER_DAY", "1800"))
PLANNER_MAX_OUTPUT_TOKENS_CAP = int(os.getenv("PLANNER_MAX_OUTPUT_TOKENS_CAP", "16000"))


def build_planner_query(planner_context_builder: Any, request: TripRequest, planner_context: Dict[str, Any]) -> str:
    """构建最终 Planner 的用户输入。"""
    prompt_context = planner_context_builder.compact_for_planner(planner_context)
    raw_context_json = json.dumps(planner_context, ensure_ascii=False, separators=(",", ":"))
    context_json = json.dumps(prompt_context, ensure_ascii=False, separators=(",", ":"))
    print(f"PlannerContext压缩: {len(raw_context_json)} -> {len(context_json)} 字符", flush=True)
    query = f"""请根据下面的 PlannerContext JSON 生成{request.city}的{request.travel_days}天旅行计划。

PlannerContext:
{context_json}

请严格遵守:
1. 只返回一个合法JSON对象，不要输出Markdown代码块、解释、前言、工具调用或<think>内容。
2. 顶层字段必须包含 city/start_date/end_date/days/weather_info/overall_suggestions/budget。
3. days长度必须等于 PlannerContext.request.travel_days，day_index从0开始，date必须逐日对应。
4. weather_info必须逐日对应 PlannerContext.tool_snapshot.trip_weather；远期天气不可用时保留“未知”，不要编造天气。
5. 景点优先使用 classic_pois、preference_pois、scenic_pois 和 experience_pois；酒店必须为null或使用hotel_pois里的真实酒店，不要把“无”“无住宿”“返程”“当天返程”写成hotel.name。单城多日行程默认连续入住同一家酒店，所有中间住宿日的day.hotel必须沿用第1晚同一家酒店，不能每天更换酒店。
6. 每天attractions必须包含1-3个景点，不能为空数组；慢节奏、亲子、老人、到达日或返程日也至少安排1个轻量候选，不要用休息、自由活动、返程替代景点。每天必须包含breakfast/lunch/dinner三餐，包括最后一天/返程日也必须安排dinner；餐饮必须具体且有多样性。lunch/dinner必须使用food_pois，并沿用候选里的name/address/location/meal_cost_hint；同一天lunch和dinner不要选择同一家餐厅；整趟行程应尽量分散使用不同餐厅和不同菜系，不要每天反复吃同一家店或同一种单品。只有当可用food_pois明显不足、忌口过滤后选择很少时，才允许少量复用真实food_pois；复用时也要优先选择已使用次数最少的候选，绝不能为了省事每天固定同一批餐厅。breakfast优先使用source_bucket=food_breakfast或meal_roles包含breakfast的food_pois；不要连续多天固定同一家早餐店或同一种早餐；到达日、赶早行程、亲子老人省力场景或住宿包含早餐时，可以写酒店早餐/民宿早餐/客栈早餐，住宿早餐可重复且不计入餐饮多样性惩罚，但不要为了写住宿早餐而漏掉breakfast。午餐和晚餐绝不能为空，绝不能使用“酒店午餐”“酒店晚餐”“民宿晚餐”“客栈晚餐”“酒店餐厅”等住宿类餐饮，绝不能把hotel_pois里的酒店/民宿/客栈/旅舍名称写成meal.name。如果最后一天晚上返程，也要安排离站/离城前的具体晚餐餐厅，不能省略dinner。选择餐饮时参考food_pois的meal_roles/cuisine_tags/diet_tags/price_level/source_bucket；avoid_risk_keywords非空的候选不要选。如果没有完美匹配当天位置、口味或预算的餐厅，宁可复用一个使用次数较少的真实food_pois，也不能写“无”、空字符串、酒店晚餐或泛化餐厅。meal.name绝不能写“早餐推荐”“午餐推荐”“晚餐推荐”“本地早餐”“当地早餐”“特色餐厅”“附近餐厅”“当地小吃”“酒店晚餐”“无”等占位词或泛化词。
7. 价格字段必须复制PlannerContext里的hint：hotel.estimated_cost=estimated_cost_hint，表示单间每晚房价；attraction.ticket_price=ticket_price_hint，表示成人单人票价；meal.estimated_cost=meal_cost_hint，表示单人单餐费用。价格复制优先级高于预算贴合；预算只能通过选择更高价的真实候选来贴近，绝不能为了凑预算修改任何候选单价。预算汇总必须考虑party.total、rooms=ceil(party.total/2)和实际住宿晚数。
8. 预算口径必须固定：total_hotels等于所有非null day.hotel.estimated_cost之和乘以rooms；total_attractions等于所有已选景点ticket_price之和乘以party.total；total_meals等于所有meal.estimated_cost之和乘以party.total；budget.total必须等于total_attractions+total_hotels+total_meals+total_transportation四项整数之和。
9. 内部生成顺序必须是：先选每天的酒店、景点和三餐；再统计实际住宿晚数和rooms；再计算四个预算分项；最后计算budget.total并只输出最终JSON。不要一边写每天行程一边凭感觉填budget。
10. 所有价格和预算字段必须是最终整数数字字面量，不能写算式、括号、加减乘除、小数或解释；先在内部算完，再把结果写成整数。不要复用提示词或示例里的任何预算数字。
11. 根据候选POI的district、address和location自行安排顺路组合，避免同一天明显跨区跳跃；如果单段路线较长，需要在description或transportation里解释。当前没有真实距离工具，hotel.distance必须写空字符串""，不要编造“距离景点2公里”“距主要景点约X公里”等伪精确距离。
12. 如果 PlannerContext.planner_constraints.budget_fit_policy 存在，budget.total 应尽量落在 target_min_total 和 target_max_total 之间；不要只做最低价方案。若真实候选价格不足以完全用满预算，选择最接近预算的真实候选组合并在overall_suggestions中说明，不能抬高免费/低价景点门票，不能复用同一家餐厅凑预算。
"""
    if request.free_text_input:
        query += f"\n额外要求: {request.free_text_input}"

    return query


def planner_max_output_tokens(request: TripRequest) -> int:
    """按行程天数动态估算 Planner 输出上限。"""
    return min(
        PLANNER_OUTPUT_BASE_TOKENS + request.travel_days * PLANNER_OUTPUT_TOKENS_PER_DAY,
        PLANNER_MAX_OUTPUT_TOKENS_CAP,
    )
