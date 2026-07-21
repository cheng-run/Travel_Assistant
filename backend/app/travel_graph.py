"""
LangGraph 多 Agent 协作编排

工作流:
    START
      ├── AttractionSearchAgent ──┐
      ├── HotelAgent ─────────────┤  并行 (fan-out)
      ├── WeatherQueryAgent ──────┘
      │         ↓
      └── PlannerAgent ──→ END      串行汇聚 (fan-in)

PlannerAgent 有 3 条入边，通过 Guard 确保数据齐全后只执行一次。
"""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.AttractionSearchAgent import attraction_search_node
from app.agents.HotelAgent import hotel_search_node
from app.agents.PlannerAgent import planner_node
from app.agents.WeatherQueryAgent import weather_query_node
from app.config import (
    NODE_ATTRACTION,
    NODE_HOTEL,
    NODE_PLANNER,
    NODE_WEATHER,
    STATE_ATTRACTIONS,
    STATE_ERROR,
    STATE_FINAL_PLAN,
    STATE_HOTELS,
    STATE_REQUEST,
    STATE_WEATHER,
)
from app.models.schemas import Attraction, Hotel, TripPlan, TripPlanRequest, WeatherInfo


class AgentState(TypedDict, total=False):
    """
    LangGraph 全局状态 — 在节点间渐进式填充。

    流程:
    1. 用户传入 request
    2. 三个子 Agent 并行写入 attractions / hotels / weather
    3. PlannerAgent 读取全部数据，写入 final_plan
    """
    request: TripPlanRequest
    attractions: list[Attraction]
    hotels: list[Hotel]
    weather: list[WeatherInfo]
    final_plan: TripPlan
    error: str


def build_travel_graph():
    """构建并编译 LangGraph 旅行规划工作流。"""
    graph = StateGraph(AgentState)

    # ── 注册节点 ──────────────────────────────────────────────────────────
    graph.add_node(NODE_ATTRACTION, attraction_search_node)
    graph.add_node(NODE_HOTEL, hotel_search_node)
    graph.add_node(NODE_WEATHER, weather_query_node)
    graph.add_node(NODE_PLANNER, planner_node)

    # ── Fan-out: 三个子 Agent 并行启动 ────────────────────────────────────
    graph.add_edge(START, NODE_ATTRACTION)
    graph.add_edge(START, NODE_HOTEL)
    graph.add_edge(START, NODE_WEATHER)

    # ── Fan-in: 汇聚到 PlannerAgent ───────────────────────────────────────
    graph.add_edge(NODE_ATTRACTION, NODE_PLANNER)
    graph.add_edge(NODE_HOTEL, NODE_PLANNER)
    graph.add_edge(NODE_WEATHER, NODE_PLANNER)

    graph.add_edge(NODE_PLANNER, END)

    return graph.compile()


# ── 模块级单例 ───────────────────────────────────────────────────────────────
travel_app = build_travel_graph()
