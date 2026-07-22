"""
AttractionSearchAgent — 景点搜索节点 (LangGraph)

节点内部使用 ReAct 模式: LLM 自主调用高德 MCP 工具搜索景点，
然后将搜索结果结构化解析为 list[Attraction]。
"""

import logging

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.llm import get_llm_for_agent, get_structured_llm
from app.agents.tools import get_mcp_tools
from app.config import (
    AGENT_ATTRACTION,
    ATTRACTION_PARSE_SYSTEM,
    ATTRACTION_SEARCH_SYSTEM,
    ATTRACTION_SEARCH_TOOLS,
    ATTRACTION_SEARCH_USER,
    ATTRACTIONS_PER_DAY_FACTOR,
    STATE_ATTRACTIONS,
    STATE_REQUEST,
)
from app.models.schemas import Attraction


class _AttractionList(BaseModel):
    """LLM 结构化输出: 景点列表"""
    attractions: list[Attraction] = Field(description="搜索到的景点列表")


async def attraction_search_node(state: dict) -> dict:
    """
    LangGraph 节点: 搜索景点。

    Args:
        state: AgentState，必须包含 STATE_REQUEST (TripPlanRequest)

    Returns:
        dict: {STATE_ATTRACTIONS: list[Attraction]}
    """
    logger = logging.getLogger(__name__)
    try:
        request = state[STATE_REQUEST]

        # ── 1. 准备 LLM ──────────────────────────────────────────────────────
        llm = get_llm_for_agent(AGENT_ATTRACTION)

        # ── 2. 获取并筛选 MCP 工具 ───────────────────────────────────────────
        all_tools = await get_mcp_tools()
        search_tools = [t for t in all_tools if t.name in ATTRACTION_SEARCH_TOOLS]

        # ── 3. 构建搜索提示 ──────────────────────────────────────────────────
        preferences_text = (
            ", ".join(request.preferences) if request.preferences
            else "不限，请推荐各类热门景点"
        )
        target_count = request.days * ATTRACTIONS_PER_DAY_FACTOR

        search_prompt = ATTRACTION_SEARCH_USER.format(
            city=request.city,
            preferences=preferences_text,
            days=request.days,
            extra=request.free_text_input or "无",
            target=target_count,
        )

        # ── 4. 创建 ReAct Agent 并执行搜索 ────────────────────────────────────
        agent = create_agent(llm, search_tools)
        result = await agent.ainvoke({
            "messages": [
                SystemMessage(content=ATTRACTION_SEARCH_SYSTEM),
                HumanMessage(content=search_prompt),
            ],
        })

        # ── 5. 结构化解析为 Attraction 列表 ───────────────────────────────────
        final_message = result["messages"][-1].content
        parser_llm = get_structured_llm()
        structured = parser_llm.with_structured_output(_AttractionList)

        parse_result: _AttractionList = await structured.ainvoke([
            SystemMessage(content=ATTRACTION_PARSE_SYSTEM),
            HumanMessage(content=final_message),
        ])

        if parse_result is None:
            logger.error("景点结构化解析返回 None")
            return {STATE_ATTRACTIONS: []}

        # 安全取值：防止 Pydantic 对象内部字段意外为 None
        attractions = getattr(parse_result, "attractions", None)
        return {STATE_ATTRACTIONS: attractions if attractions else []}

    except Exception:
        logger.exception("景点搜索失败，返回空列表")
        return {STATE_ATTRACTIONS: []}
