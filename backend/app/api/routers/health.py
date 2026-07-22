"""
健康检查路由

GET /api/health → 返回服务状态和各 API Key 配置情况。
"""

# ═══════════════════════════════════════════════════════════════════════
# FastAPI 知识点 1: 最简单的端点
#   - 无路径参数、无查询参数、无请求体
#   - @router.get("/health") 定义 GET 方法
#   - 返回一个 dict，FastAPI 自动转为 JSON
#
# FastAPI 知识点 2: 为什么这里用 os.getenv 而不是 from app.config import
#   config.py 在 API Key 缺失时会抛出 RuntimeError，导致整个应用无法启动。
#   但健康检查端点应该在"任何情况"下都能返回信息，方便排查问题。
#   所以我们直接用 os.getenv 读取，不触发 config.py 的校验逻辑。
# ═══════════════════════════════════════════════════════════════════════

import os

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    系统健康检查。

    返回服务运行状态，以及各 API Key 是否已配置（不泄露 Key 内容）。
    可用于 Docker/K8s 存活探针，或前端在调用规划接口前确认后端就绪。
    """
    return {
        "status": "ok",
        "service": "Travel Assistant API",
        "version": "0.1.0",
        "deepseek_configured": bool(os.getenv("DEEPSEEK_API_KEY")),
        "amap_configured": bool(os.getenv("AMAP_API_KEY")),
        "unsplash_configured": bool(os.getenv("UNSPLASH_API_KEY")),
    }
