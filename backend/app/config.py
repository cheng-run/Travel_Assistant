"""
Travel Assistant 统一配置

所有环境变量、LLM 参数、MCP 设置、Agent Prompt、业务常量集中管理。
其他模块通过 `from app.config import xxx` 引用，不再直接读 os.getenv。
"""

import logging
import os

from dotenv import load_dotenv

# ═══════════════════════════════════════════════════════════════════════════════
# 1. 环境变量
# ═══════════════════════════════════════════════════════════════════════════════

load_dotenv()

# ── DeepSeek ──────────────────────────────────────────────────────────────────
DEEPSEEK_MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# ── 高德地图 ──────────────────────────────────────────────────────────────────
AMAP_API_KEY = os.getenv("AMAP_API_KEY")

# ── 其他（预留） ──────────────────────────────────────────────────────────────
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
POSTGRESQL_PASSWORD = os.getenv("POSTGRESQL_PASSWORD")
UNSPLASH_API_KEY = os.getenv("UNSPLASH_API_KEY")

# ── 校验必需变量 ──────────────────────────────────────────────────────────────
if not DEEPSEEK_API_KEY:
    raise RuntimeError("缺少 DEEPSEEK_API_KEY，请在 .env 中设置")
if not DEEPSEEK_MODEL_NAME:
    raise RuntimeError("缺少 DEEPSEEK_MODEL_NAME，请在 .env 中设置")
if not AMAP_API_KEY:
    raise RuntimeError("缺少 AMAP_API_KEY，请在 .env 中设置")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. LLM 配置
# ═══════════════════════════════════════════════════════════════════════════════

# ── 模型 ──────────────────────────────────────────────────────────────────────
LLM_MODEL = f"deepseek:{DEEPSEEK_MODEL_NAME}"

# ── 默认参数 ──────────────────────────────────────────────────────────────────
LLM_DEFAULT_TEMPERATURE = 0.7
LLM_DEFAULT_MAX_TOKENS = None  # None = 不限制

# ── 结构化输出专用 (禁用 thinking mode，否则与 tool_choice 冲突) ──────────────
LLM_STRUCTURED_TEMPERATURE = 0.3
LLM_STRUCTURED_EXTRA_BODY = {"thinking": {"type": "disabled"}}

# ── 各 Agent 的温度调优 ───────────────────────────────────────────────────────
AGENT_TEMPERATURE = {
    "attraction": 0.8,  # 景点推荐需要多样性
    "hotel": 0.6,       # 酒店搜索适中
    "weather": 0.3,     # 天气信息需要准确
    "planner": 0.4,     # 行程规划需要逻辑
}


# ═══════════════════════════════════════════════════════════════════════════════
# 3. MCP / 高德地图配置
# ═══════════════════════════════════════════════════════════════════════════════

AMAP_BASE_URL = "https://restapi.amap.com"
AMAP_HTTP_TIMEOUT = 30.0  # 秒
AMAP_LOG_LEVEL = logging.INFO

# ── MCP Server 路径 (相对于 backend/app/services/) ───────────────────────────
_MCP_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_SERVER_PATH = os.path.join(_MCP_DIR, "services", "amap-mcp-server.py")
MCP_SERVER_NAME = "amap"
MCP_TRANSPORT = "stdio"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Agent Prompt 模板
# ═══════════════════════════════════════════════════════════════════════════════

# ── AttractionSearchAgent ─────────────────────────────────────────────────────

ATTRACTION_SEARCH_SYSTEM = (
    "你是一个资深的旅行规划师，擅长推荐旅游景点。"
    "请根据用户的目的地城市和偏好，推荐真实存在的景点。"
    "确保: 景点名称真实、地址准确、游览时间合理、门票价格合理。"
    "尽可能覆盖不同类型的景点（自然风光、人文历史、美食街区、购物中心等）。"
)

ATTRACTION_SEARCH_USER = """\
## 用户需求
- 目的地: {city}
- 偏好类型: {preferences}
- 旅行天数: {days} 天
- 额外要求: {extra}

## 搜索策略
1. 首先用 amap_text_search 搜索 "{city}" 的主要景点
   - 如果用户有偏好（如"自然风光"），搜索对应关键词
   - 同时用 types="110000" 限定景点类别
2. 对评分 ≥ 4.0 的热门景点，用 amap_poi_detail 获取详细信息
3. 如果某些景点位置不够明确，用 amap_geocode 补充坐标
4. 目标: 找到至少 {target} 个景点，覆盖不同类型

## 输出要求
搜索完成后，请输出一份详细的景点报告，每个景点包含:
- 名称、地址、经纬度坐标
- 评分 (rating)、门票价格 (cost 字段即人均消费)
- 类别 (category)
- 建议游览时间 (根据景点规模和类型合理估算，单位: 分钟)
- 简要描述 (根据类别和位置总结)\
"""

ATTRACTION_PARSE_SYSTEM = (
    "你是一个数据整理助手。请从以下景点搜索报告中提取所有景点信息，"
    "整理为结构化的景点列表。\n"
    "要求:\n"
    "- 每个景点必须包含 name, address, location (longitude/latitude)\n"
    "- visit_duration 根据景点规模合理估算 (小型景点60-120分钟, 大型景点180-360分钟)\n"
    "- ticket_price 从搜索结果的 cost 字段映射，无数据则填 0\n"
    "- rating 从搜索结果映射，无数据则填 None\n"
    "- description 用中文简要描述该景点特色 (50-100字)\n"
    "- 保留搜索到的所有景点，不要遗漏"
)

# ── HotelAgent ────────────────────────────────────────────────────────────────

HOTEL_SEARCH_SYSTEM = "你是一个专业的酒店搜索助手。"

HOTEL_SEARCH_USER = """\
## 用户需求
- 目的地: {city}
- 住宿偏好: {accommodation}
- 旅行天数: {days} 天
- 额外要求: {extra}

## 搜索策略
根据住宿偏好调整搜索关键词:
- "经济型"/"快捷" → 搜索 "经济型酒店"、"快捷酒店"，优先 cost 较低的
- "舒适型"/"三星"/"商务" → 搜索 "商务酒店"、"三星级酒店"
- "豪华型"/"五星"/"高端" → 搜索 "五星级酒店"、"豪华酒店"，优先高评分
- 未指定 → 覆盖各价位

操作步骤:
1. 用 amap_text_search 搜索酒店，types="060000" (酒店类别)
   - 根据偏好调整 keywords 参数
2. 对评分较高的酒店，用 amap_poi_detail 获取详细信息（电话、评分等）
3. 目标: 找到 {target_min} 到 {target_max} 个酒店，覆盖不同价位和地段

## 输出要求
搜索完成后，请输出每个酒店的:
- 名称、地址、经纬度坐标
- 价格范围 (根据 cost/price_range 字段推断: 经济/舒适/豪华)
- 评分 (rating)
- 距离市中心/景点的距离 (如有)
- 预估每晚费用 (estimated_cost)\
"""

HOTEL_PARSE_SYSTEM = (
    "你是一个数据整理助手。请从以下酒店搜索报告中提取所有酒店信息，"
    "整理为结构化的酒店列表。\n"
    "要求:\n"
    "- 每个酒店必须包含 name, address\n"
    "- location 包含 longitude/latitude，无数据则填 0\n"
    "- price_range 使用中文: 经济/舒适/豪华/奢华\n"
    "- rating 转换为字符串 (如 '4.5')\n"
    "- distance 如有距离信息则填入\n"
    "- type 填入酒店类型 (如: 经济型酒店/商务酒店/五星级酒店/民宿)\n"
    "- estimated_cost 根据 cost 字段或价格范围合理估算 (元/晚)\n"
    "- 保留搜索到的所有酒店，不要遗漏"
)

# ── WeatherQueryAgent ─────────────────────────────────────────────────────────

WEATHER_SEARCH_SYSTEM = "你是一个天气查询助手。"

WEATHER_SEARCH_USER = """\
你是一个天气查询助手。请查询用户旅行目的地的天气情况。

## 用户需求
- 目的地: {city}
- 旅行日期: {start_date} 至 {end_date}（共 {days} 天）
- 额外要求: {extra}

## 操作步骤
1. 用 amap_weather 工具查询 "{city}" 的天气（使用 extensions="all" 获取预报）
2. 整理每天的天气预报信息

## 输出要求
查询完成后，请输出每天的天气信息，包含:
- 日期、白天天气、夜间天气
- 白天温度、夜间温度（摄氏度）
- 风向、风力\
"""

WEATHER_PARSE_SYSTEM = (
    "你是一个数据整理助手。请从以下天气查询报告中提取每天的天气信息，"
    "整理为结构化的天气列表。\n"
    "要求:\n"
    "- 每天一条记录，日期格式为 YYYY-MM-DD\n"
    "- day_weather / night_weather 使用中文（如: 晴、多云、小雨、大雨）\n"
    "- day_temp / night_temp 只保留数字（去掉 °C 后缀）\n"
    "- wind_direction 使用中文（如: 南风、东北风）\n"
    "- wind_power 使用原始值（如: ≤3、4-5级）\n"
    "- 保留查询到的所有天数，不要遗漏"
)

# ── PlannerAgent ──────────────────────────────────────────────────────────────

PLANNER_SYSTEM = (
    "你是一个资深的旅行规划师。请根据提供的景点、酒店、天气信息，"
    "制定详细的每日旅行计划。\n\n"
    "规划要求:\n"
    "1. 每天安排 2-3 个景点，考虑景点之间的地理位置邻近性\n"
    "2. 根据天气调整户外/室内景点（雨天优先室内、高温避开正午户外）\n"
    "3. 每天安排早餐、午餐、晚餐（根据景点位置推荐就近餐饮，估算费用）\n"
    "4. 合理安排住宿（根据景点分布选择最近的酒店）\n"
    "5. 给出每天的交通方式建议\n"
    "6. 编制详细预算（景点门票 + 酒店 + 餐饮 + 交通）\n"
    "7. 给出总体旅行建议（穿衣、注意事项等）\n\n"
    "输出格式:\n"
    "- days: 每天的行程，day_index 从 0 开始\n"
    "- 每个 DayPlan 包含: date, description, transportation, accommodation, hotel, attractions, meals\n"
    "- weather_info: 直接引用提供的天气数据\n"
    "- overall_suggestions: 综合建议（100-200字）\n"
    "- budget: 汇总各项费用"
)

PLANNER_USER = """\
## 用户需求
- 目的地: {city}
- 日期: {start_date} 至 {end_date}（共 {days} 天）
- 交通方式: {transportation}
- 住宿偏好: {accommodation}
- 旅行偏好: {preferences}
- 额外要求: {extra}

## 可选景点 ({attraction_count} 个)
{attractions}

## 可选酒店 ({hotel_count} 个)
{hotels}

## 天气预报 ({weather_count} 天)
{weather}

请基于以上信息生成完整的旅行计划。\
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 5. 业务常量
# ═══════════════════════════════════════════════════════════════════════════════

# ── Agent 使用的 MCP 工具名 ───────────────────────────────────────────────────
ATTRACTION_SEARCH_TOOLS = {
    "amap_text_search",
    "amap_around_search",
    "amap_poi_detail",
    "amap_geocode",
}

HOTEL_SEARCH_TOOLS = {
    "amap_text_search",
    "amap_around_search",
    "amap_poi_detail",
    "amap_geocode",
}

WEATHER_TOOLS = {"amap_weather"}

# ── 搜索结果数量 ──────────────────────────────────────────────────────────────
ATTRACTIONS_PER_DAY_FACTOR = 3   # 每天备选景点数 = days × 3
HOTELS_MIN_COUNT = 3              # 酒店最少推荐数
HOTELS_PER_DAY_FACTOR = 1         # 每多一天增加的备选酒店数

# ── LangGraph State & Node 名称 ───────────────────────────────────────────────
STATE_REQUEST = "request"
STATE_ATTRACTIONS = "attractions"
STATE_HOTELS = "hotels"
STATE_WEATHER = "weather"
STATE_FINAL_PLAN = "final_plan"
STATE_ERROR = "error"

NODE_ATTRACTION = "attraction_search"
NODE_HOTEL = "hotel_search"
NODE_WEATHER = "weather_query"
NODE_PLANNER = "planner"

# ── Agent 名称 (用于 get_llm_for_agent) ───────────────────────────────────────
AGENT_ATTRACTION = "attraction"
AGENT_HOTEL = "hotel"
AGENT_WEATHER = "weather"
AGENT_PLANNER = "planner"
