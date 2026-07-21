"""
LLM 工厂 — 所有 Agent 调用 LLM 的统一入口。

配置集中管理在 app.config，本模块只负责创建 LLM 实例。
"""

from langchain.chat_models import init_chat_model

from app.config import (
    AGENT_TEMPERATURE,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    LLM_DEFAULT_MAX_TOKENS,
    LLM_DEFAULT_TEMPERATURE,
    LLM_MODEL,
    LLM_STRUCTURED_EXTRA_BODY,
    LLM_STRUCTURED_TEMPERATURE,
)


def get_llm(
    temperature: float = LLM_DEFAULT_TEMPERATURE,
    max_tokens: int | None = LLM_DEFAULT_MAX_TOKENS,
    **kwargs,
):
    """
    返回 DeepSeek LLM 实例。

    Args:
        temperature: 采样温度 (默认 0.7)
        max_tokens: 最大输出 token (默认不限)
        **kwargs: 传递给 init_chat_model 的额外参数

    Returns:
        BaseChatModel — 支持 .invoke() / .with_structured_output()
    """
    return init_chat_model(
        model=LLM_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        **kwargs,
    )


def get_structured_llm(temperature: float = LLM_STRUCTURED_TEMPERATURE):
    """
    返回禁用 thinking mode 的 LLM，专用于 with_structured_output()。

    DeepSeek 的 thinking mode 与 tool_choice 冲突，
    with_structured_output 内部使用 tool_choice 强制结构化输出。
    """
    return get_llm(temperature=temperature, extra_body=LLM_STRUCTURED_EXTRA_BODY)


def get_llm_for_agent(agent: str):
    """为指定 Agent 获取调优温度的 LLM。agent ∈ {attraction, hotel, weather, planner}"""
    return get_llm(temperature=AGENT_TEMPERATURE.get(agent, LLM_DEFAULT_TEMPERATURE))
