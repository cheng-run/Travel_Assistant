"""
PlannerAgent — 行程规划节点 (LangGraph)

纯 LLM 整合节点，不调用任何外部工具。
接收三个子 Agent 的结果，综合生成完整的 TripPlan。

关键设计: PlannerAgent 有 3 条入边（被调用 3 次），
通过 Guard 确保只在数据齐全时执行一次实际规划。
"""

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm import get_structured_llm
from app.config import (
    PLANNER_SYSTEM,
    PLANNER_USER,
    STATE_ATTRACTIONS,
    STATE_FINAL_PLAN,
    STATE_HOTELS,
    STATE_REQUEST,
    STATE_WEATHER,
)
from app.models.schemas import TripPlan


def planner_node(state: dict) -> dict:
    """
    LangGraph 节点: 整合所有信息，生成完整旅行计划。

    Guard 逻辑:
    - 3 个并行子 Agent 完成后各自触发本节点
    - 前 2 次调用时数据不全 → return {}（no-op）
    - 最后 1 次调用时所有数据就绪 → 执行规划

    Args:
        state: AgentState，需包含 request, attractions, hotels, weather

    Returns:
        dict: {STATE_FINAL_PLAN: TripPlan} 或 {} (guard)
    """
    # ── Guard: 等待所有并行 Agent 完成 ──────────────────────────────────────
    if (
        STATE_ATTRACTIONS not in state
        or STATE_HOTELS not in state
        or STATE_WEATHER not in state
    ):
        return {}

    # ── 所有数据就绪 ─────────────────────────────────────────────────────────
    request = state[STATE_REQUEST]
    attractions = state[STATE_ATTRACTIONS]
    hotels = state[STATE_HOTELS]
    weather = state[STATE_WEATHER]

    # ── 将子 Agent 结果序列化为文本 ──────────────────────────────────────────
    attractions_text = "\n".join(
        f"- {a.name} | {a.address} | "
        f"坐标({a.location.longitude:.4f},{a.location.latitude:.4f}) | "
        f"评分{a.rating} | 门票{a.ticket_price}元 | 游览{a.visit_duration}分钟 | "
        f"类别:{a.category} | {a.description}"
        for a in attractions
    )

    hotels_text = "\n".join(
        f"- {h.name} | {h.address} | "
        f"类型:{h.type} | {h.price_range} | 评分{h.rating} | "
        f"约{h.estimated_cost}元/晚"
        for h in hotels
    )

    weather_text = "\n".join(
        f"- {w.date}: 白天{w.day_weather} {w.day_temp}°C / "
        f"夜间{w.night_weather} {w.night_temp}°C | "
        f"{w.wind_direction}{w.wind_power}"
        for w in weather
    )

    # ── LLM 规划 ─────────────────────────────────────────────────────────────
    preferences_text = (
        ", ".join(request.preferences) if request.preferences else "无"
    )

    user_prompt = PLANNER_USER.format(
        city=request.city,
        start_date=request.start_date,
        end_date=request.end_date,
        days=request.days,
        transportation=request.transportation,
        accommodation=request.accommodation,
        preferences=preferences_text,
        extra=request.free_text_input or "无",
        attraction_count=len(attractions),
        attractions=attractions_text,
        hotel_count=len(hotels),
        hotels=hotels_text,
        weather_count=len(weather),
        weather=weather_text,
    )

    llm = get_structured_llm()
    structured = llm.with_structured_output(TripPlan)

    plan: TripPlan = structured.invoke([
        SystemMessage(content=PLANNER_SYSTEM),
        HumanMessage(content=user_prompt),
    ])

    return {STATE_FINAL_PLAN: plan}
