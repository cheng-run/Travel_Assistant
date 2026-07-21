"""
HotelAgent — 酒店搜索节点 (LangGraph)

节点内部使用 ReAct 模式: LLM 理解用户住宿偏好，调用高德 POI 工具
搜索酒店，然后结构化解析为 list[Hotel]。
"""

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.llm import get_llm_for_agent, get_structured_llm
from app.agents.tools import get_mcp_tools
from app.config import (
    AGENT_HOTEL,
    HOTEL_PARSE_SYSTEM,
    HOTEL_SEARCH_SYSTEM,
    HOTEL_SEARCH_TOOLS,
    HOTEL_SEARCH_USER,
    HOTELS_MIN_COUNT,
    HOTELS_PER_DAY_FACTOR,
    STATE_HOTELS,
    STATE_REQUEST,
)
from app.models.schemas import Hotel


class _HotelList(BaseModel):
    """LLM 结构化输出: 酒店列表"""
    hotels: list[Hotel] = Field(description="搜索到的酒店列表")


async def hotel_search_node(state: dict) -> dict:
    """
    LangGraph 节点: 搜索酒店。

    Args:
        state: AgentState，必须包含 STATE_REQUEST (TripPlanRequest)

    Returns:
        dict: {STATE_HOTELS: list[Hotel]}
    """
    request = state[STATE_REQUEST]

    # ── 1. 准备 LLM ──────────────────────────────────────────────────────────
    llm = get_llm_for_agent(AGENT_HOTEL)

    # ── 2. 获取并筛选 MCP 工具 ───────────────────────────────────────────────
    all_tools = await get_mcp_tools()
    search_tools = [t for t in all_tools if t.name in HOTEL_SEARCH_TOOLS]

    # ── 3. 构建搜索提示 ──────────────────────────────────────────────────────
    accommodation = request.accommodation or "未指定"
    target_min = max(HOTELS_MIN_COUNT, request.days + HOTELS_PER_DAY_FACTOR)

    search_prompt = HOTEL_SEARCH_USER.format(
        city=request.city,
        accommodation=accommodation,
        days=request.days,
        extra=request.free_text_input or "无",
        target_min=target_min,
        target_max=target_min + 3,
    )

    # ── 4. 创建 ReAct Agent 并执行搜索 ────────────────────────────────────────
    agent = create_agent(llm, search_tools)
    result = await agent.ainvoke({
        "messages": [
            SystemMessage(content=HOTEL_SEARCH_SYSTEM),
            HumanMessage(content=search_prompt),
        ],
    })

    # ── 5. 结构化解析为 Hotel 列表 ───────────────────────────────────────────
    final_message = result["messages"][-1].content
    parser_llm = get_structured_llm()
    structured = parser_llm.with_structured_output(_HotelList)

    parse_result: _HotelList = await structured.ainvoke([
        SystemMessage(content=HOTEL_PARSE_SYSTEM),
        HumanMessage(content=final_message),
    ])

    return {STATE_HOTELS: parse_result.hotels}
