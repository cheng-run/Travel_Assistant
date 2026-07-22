"""
旅行规划路由

POST /api/travel/plan → 提交旅行需求，运行 LangGraph 多 Agent 协作，返回完整旅行计划
"""

# ═══════════════════════════════════════════════════════════════════════
# FastAPI 知识点:
#   请求体 (Request Body):
#     request: TripPlanRequest → FastAPI 自动从 POST 的 JSON body 解析数据，
#     用 Pydantic v2 校验（类型、范围、必填字段），校验失败返回 422。
#
#   response_model:
#     response_model=TripPlan 让 FastAPI:
#       1) 输出前用 TripPlan 模型校验响应数据
#       2) 过滤掉模型中未定义的额外字段
#       3) 自动生成 OpenAPI schema (显示在 Swagger UI)
#
#   async def:
#     虽然 LangGraph 内部会用线程跑同步代码，但 travel_app.ainvoke()
#     是真正的异步调用，不会阻塞 FastAPI 的事件循环。
# ═══════════════════════════════════════════════════════════════════════

import httpx
import logging
from fastapi import APIRouter, HTTPException
from app.models.schemas import TripPlanRequest, TripPlan
from app.travel_graph import travel_app

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/plan",
    response_model=TripPlan,
    summary="生成旅行计划",
    description="提交目的地、日期、偏好等信息，AI 自动搜索景点/酒店/天气，生成完整旅行计划。",
)
async def create_travel_plan(request: TripPlanRequest):
    """
    提交旅行需求，运行 LangGraph 多 Agent 规划流程。

    内部流程（约 30-90 秒）：
    1. 三个子 Agent 并行搜索：景点、酒店、天气
    2. PlannerAgent 整合所有信息，生成每日行程 + 预算
    """
    try:
        # travel_app 是在 travel_graph.py 中编译好的 LangGraph 单例
        # ainvoke() 是异步入口，内部自动协调 3 个并行 Agent 节点
        logger.info("收到旅行规划请求: city=%s, days=%d", request.city, request.days)
        result = await travel_app.ainvoke({"request": request})
        final_plan: TripPlan | None = result.get("final_plan")

        if final_plan is None:
            # 诊断哪些 Agent 未能产出数据
            missing = []
            if not result.get("attractions"):
                missing.append("景点搜索")
            if not result.get("hotels"):
                missing.append("酒店搜索")
            if not result.get("weather"):
                missing.append("天气查询")

            reason = "、".join(missing) if missing else "规划整合"
            detail = f"AI 规划失败：{reason}未返回有效结果，请稍后重试"
            logger.error("旅行规划失败: city=%s, missing=%s", request.city, missing)
            raise HTTPException(status_code=500, detail=detail)

        logger.info("旅行规划完成: city=%s", request.city)
        return final_plan

    except HTTPException:
        # 已包装的 HTTP 异常直接透传，不重复包装
        raise
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="AI 服务响应超时，请稍后重试",
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=502,
            detail="无法连接 AI 服务（DeepSeek），请检查网络和 API Key 配置",
        )
    except Exception as e:
        logger.exception("旅行规划失败: city=%s", request.city)
        raise HTTPException(
            status_code=500,
            detail=f"旅行规划失败：{str(e)}",
        )
