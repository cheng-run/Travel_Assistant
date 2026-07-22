"""
WeatherQueryAgent — 天气查询节点 (LangGraph)

节点内部使用 ReAct 模式: LLM 调用高德 amap_weather 工具获取天气数据，
然后结构化解析为 list[WeatherInfo]。
"""

import logging

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.llm import get_llm_for_agent, get_structured_llm
from app.agents.tools import get_mcp_tools
from app.config import (
    AGENT_WEATHER,
    STATE_REQUEST,
    STATE_WEATHER,
    WEATHER_PARSE_SYSTEM,
    WEATHER_SEARCH_SYSTEM,
    WEATHER_SEARCH_USER,
    WEATHER_TOOLS,
)
from app.models.schemas import WeatherInfo


class _WeatherList(BaseModel):
    """LLM 结构化输出: 天气信息列表"""
    weather_info: list[WeatherInfo] = Field(description="每日天气信息列表")


async def weather_query_node(state: dict) -> dict:
    """
    LangGraph 节点: 查询旅行期间的天气。

    Args:
        state: AgentState，必须包含 STATE_REQUEST (TripPlanRequest)

    Returns:
        dict: {STATE_WEATHER: list[WeatherInfo]}
    """
    logger = logging.getLogger(__name__)
    try:
        request = state[STATE_REQUEST]

        # ── 1. 准备 LLM ──────────────────────────────────────────────────────
        llm = get_llm_for_agent(AGENT_WEATHER)

        # ── 2. 获取并筛选 MCP 工具 ───────────────────────────────────────────
        all_tools = await get_mcp_tools()
        weather_tools = [t for t in all_tools if t.name in WEATHER_TOOLS]

        # ── 3. 构建查询提示 ──────────────────────────────────────────────────
        query_prompt = WEATHER_SEARCH_USER.format(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=request.days,
            extra=request.free_text_input or "无",
        )

        # ── 4. 创建 ReAct Agent 并执行查询 ────────────────────────────────────
        agent = create_agent(llm, weather_tools)
        result = await agent.ainvoke({
            "messages": [
                SystemMessage(content=WEATHER_SEARCH_SYSTEM),
                HumanMessage(content=query_prompt),
            ],
        })

        # ── 5. 结构化解析为 WeatherInfo 列表 ──────────────────────────────────
        final_message = result["messages"][-1].content
        parser_llm = get_structured_llm()
        structured = parser_llm.with_structured_output(_WeatherList)

        parse_result: _WeatherList = await structured.ainvoke([
            SystemMessage(content=WEATHER_PARSE_SYSTEM),
            HumanMessage(content=final_message),
        ])

        if parse_result is None:
            logger.error("天气结构化解析返回 None")
            return {STATE_WEATHER: []}

        return {STATE_WEATHER: parse_result.weather_info}

    except Exception:
        logger.exception("天气查询失败，返回空列表")
        return {STATE_WEATHER: []}
