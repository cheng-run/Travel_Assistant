"""
MCP 工具集成 — 将高德 MCP Server 的工具暴露为 LangChain Tool 列表。

所有 Agent 通过 `await get_mcp_tools()` 获取工具列表，
无需关心 MCP 子进程的生命周期管理。
"""

import sys

from langchain_mcp_adapters.client import MultiServerMCPClient

from app.config import MCP_SERVER_NAME, MCP_SERVER_PATH, MCP_TRANSPORT

# 全局单例: 复用同一个 MCP 子进程，避免重复启动
_client: MultiServerMCPClient | None = None


async def get_mcp_tools():
    """
    获取高德地图 MCP 工具列表 (LangChain Tool 对象)。

    首次调用时启动 MCP Server 子进程并建立 stdio 连接。
    后续调用复用已有连接，避免重复创建子进程。

    Returns:
        list[BaseTool]: 9 个高德地图工具 (amap_text_search, amap_geocode, ...)
    """
    global _client
    if _client is None:
        _client = MultiServerMCPClient({
            MCP_SERVER_NAME: {
                "command": sys.executable,
                "args": [MCP_SERVER_PATH],
                "transport": MCP_TRANSPORT,
            },
        })
    return await _client.get_tools()
