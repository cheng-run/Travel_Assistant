"""
Travel Assistant API — FastAPI 应用入口

将 LangGraph 旅行规划和 Unsplash 图片搜索封装为 RESTful API。

运行方式:
    uv run python -m app.api.main
    或: uv run uvicorn app.api.main:app --reload --port 8000

启动后访问:
    Swagger UI (交互式文档): http://localhost:8000/docs
    ReDoc (只读文档):       http://localhost:8000/redoc
    健康检查:               http://localhost:8000/api/health
"""

# ═══════════════════════════════════════════════════════════════════════
# FastAPI 知识点:
#   FastAPI() 是应用核心，类似 Flask 的 Flask(__name__)。
#   它管理路由、中间件、生命周期、依赖注入、OpenAPI 文档。
#
#   CORS（跨域资源共享）:
#     浏览器安全策略会阻止一个域名下的 JS 请求另一个域名。
#     CORSMiddleware 让后端声明"允许来自 http://localhost:3000 的请求"。
#     开发阶段 allow_origins=["*"] 允许所有来源，上线后应限制具体域名。
#
#   app.include_router():
#     把子路由挂载到主应用上。prefix 参数给该 router 下所有路径加前缀。
#     如 router 里定义 @router.get("/health")，prefix="/api" → 实际路径 /api/health
#     tags=["xxx"] 让 Swagger UI 按功能分组展示。
#
#   lifespan:
#     替代旧版 @app.on_event("startup") / @app.on_event("shutdown")。
#     yield 之前是启动逻辑，yield 之后是关闭逻辑。
# ═══════════════════════════════════════════════════════════════════════

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import health, attractions, travel

# ── 日志 ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


# ── 生命周期 ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动 / 关闭时的钩子函数。"""
    logger.info("=" * 50)
    logger.info("🚀 Travel Assistant API 启动中...")
    logger.info("📍 Swagger UI: http://localhost:8000/docs")
    logger.info("📍 Health:     http://localhost:8000/api/health")
    logger.info("=" * 50)
    yield  # ← 应用在此运行
    logger.info("Travel Assistant API 已关闭")


# ── FastAPI 实例 ──────────────────────────────────────────────────────
app = FastAPI(
    title="Travel Assistant API",
    description="AI 驱动的旅行规划助手 — 搜索景点/酒店/天气，生成完整旅行计划",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS 中间件 ───────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 路由注册 ──────────────────────────────────────────────────────────
# 每个 include_router 的 prefix 会成为该 router 下所有路径的前缀
app.include_router(health.router, prefix="/api", tags=["系统"])
app.include_router(attractions.router, prefix="/api/attractions", tags=["景点图片"])
app.include_router(travel.router, prefix="/api/travel", tags=["旅行规划"])

# ═══════════════════════════════════════════════════════════════════════
# 启动入口
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn

    # uvicorn.run() 参数说明:
    #   "app.api.main:app" = "模块路径:FastAPI实例变量名"
    #   host="0.0.0.0" → 监听所有网络接口（局域网内可访问）
    #   reload=True    → 代码修改后自动重启（开发模式）
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
