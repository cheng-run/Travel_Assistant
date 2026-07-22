"""
Travel Assistant API 启动脚本

直接运行本文件即可启动开发服务器（带热重载）。

运行方式:
    cd backend
    uv run python run.py

也等同于:
    uv run uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
"""

# ═══════════════════════════════════════════════════════════════════════
# uvicorn 是什么？
#   uvicorn 是一个基于 uvloop 和 httptools 的高性能 ASGI 服务器。
#   它负责接收 HTTP 请求、管理连接池、把请求转发给 FastAPI 应用。
#   对于 async 框架（如 FastAPI），uvicorn 比传统的 gunicorn 更合适。
#
# uvicorn.run() 参数:
#   "app.api.main:app"  → 模块路径 : FastAPI 实例变量名
#   host="0.0.0.0"      → 监听所有网络接口（局域网内其他设备可访问）
#   port=8000           → 默认端口，可改为其他值
#   reload=True         → 开发模式：代码修改后自动重启（生产环境应设 False）
#   log_level="info"    → 请求日志输出到控制台
# ═══════════════════════════════════════════════════════════════════════

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
