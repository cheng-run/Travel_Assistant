"""
高德地图 MCP Server — 为 Travel Assistant Agent 提供 9 个地理工具。

工具列表:
    amap_text_search        POI 关键字搜索
    amap_around_search      周边 POI 搜索
    amap_poi_detail         POI 详情查询
    amap_geocode            地址 → 坐标
    amap_reverse_geocode    坐标 → 地址
    amap_weather            城市天气 (组合: 行政区划 + 天气 API)
    amap_distance           两点距离/时间
    amap_driving_route      驾车路径规划
    amap_walking_route      步行路径规划

运行方式:
    python backend/app/services/amap-mcp-server.py

通过 stdio 与 Agent 通信，由 langchain-mcp-adapters 的 MultiServerMCPClient 启动为子进程。
"""

import logging
import sys
from pathlib import Path
from typing import Any

# 确保 backend/ 在 sys.path 上（MCP Server 作为独立子进程运行时需要）
_sys_path = str(Path(__file__).resolve().parent.parent.parent)
if _sys_path not in sys.path:
    sys.path.insert(0, _sys_path)

import httpx
from mcp.server.fastmcp import FastMCP

from app.config import AMAP_API_KEY, AMAP_BASE_URL, AMAP_HTTP_TIMEOUT, AMAP_LOG_LEVEL, MCP_SERVER_NAME

# ═══════════════════════════════════════════════════════════════════════════════
# Bootstrap
# ═══════════════════════════════════════════════════════════════════════════════

# ── 日志 (必须输出到 stderr！stdout 是 MCP JSON-RPC 传输通道) ─────────────────
logger = logging.getLogger("amap-mcp")
logger.setLevel(AMAP_LOG_LEVEL)
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
logger.addHandler(handler)

# ── MCP Server 实例 ───────────────────────────────────────────────────────────
mcp = FastMCP(MCP_SERVER_NAME)

# ── 共享 HTTP 客户端 ─────────────────────────────────────────────────────────
_client = httpx.Client(timeout=AMAP_HTTP_TIMEOUT)


# ═══════════════════════════════════════════════════════════════════════════════
# 异常 & 工具函数
# ═══════════════════════════════════════════════════════════════════════════════

class AmapAPIError(Exception):
    """高德 API 返回非成功状态时抛出。"""
    def __init__(self, infocode: str, info: str, path: str):
        self.infocode = infocode
        self.info = info
        self.path = path
        super().__init__(f"Amap API error [{infocode}] on {path}: {info}")


def _amap_get(path: str, **params: Any) -> dict:
    """
    发送 GET 请求到高德 API。

    自动注入 API Key、检查 HTTP 状态码、验证高德业务状态码 (status=="1")。
    所有 Tool 函数通过此入口调用高德 API，确保错误处理一致。
    """
    params["key"] = AMAP_API_KEY
    logger.debug("GET %s params=%s", path, {k: v for k, v in params.items() if k != "key"})

    resp = _client.get(f"{AMAP_BASE_URL}{path}", params=params)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "1":
        raise AmapAPIError(
            infocode=data.get("infocode", "?"),
            info=data.get("info", "Unknown error"),
            path=path,
        )
    return data


def _parse_location(loc_str: str) -> dict[str, float]:
    """解析高德坐标字符串 '116.397,39.909' → {'lng': 116.397, 'lat': 39.909}"""
    l, r = loc_str.split(",", 1)
    return {"lng": float(l.strip()), "lat": float(r.strip())}


def _get_adcode(city_name: str) -> str:
    """
    通过行政区划 API 将城市名解析为 6 位 adcode。

    高德天气 API 要求传数字 adcode (如 "110000")，Agent 只知道城市名。
    此函数封装了 adcode 解析，使 amap_weather 对 Agent 暴露为单次调用。
    """
    data = _amap_get("/v3/config/district", keywords=city_name, subdistrict=0)
    districts = data.get("districts", [])
    if not districts:
        raise ValueError(f"无法找到城市 '{city_name}' 的行政区划代码")
    return districts[0].get("adcode", "")


# ═══════════════════════════════════════════════════════════════════════════════
# 响应格式化 (裁剪原始响应，减少 token 消耗)
# ═══════════════════════════════════════════════════════════════════════════════

def _format_poi(raw: dict) -> dict:
    """将原始 POI 字典裁剪为 Agent 需要的关键字段 (~15 字段 vs 原始 30+)"""
    loc_str = raw.get("location", "")
    result: dict[str, Any] = {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "address": raw.get("address"),
        "location": _parse_location(loc_str) if loc_str else None,
        "province": raw.get("pname"),
        "city": raw.get("cityname"),
        "district": raw.get("adname"),
        "category": raw.get("type"),
        "typecode": raw.get("typecode"),
        "tel": raw.get("tel", ""),
        "distance": raw.get("distance"),
    }

    # 扩展信息: 评分 & 人均消费
    biz_ext = raw.get("biz_ext", {})
    if biz_ext:
        result["rating"] = biz_ext.get("rating")
        result["cost"] = biz_ext.get("cost")

    # 照片
    photos = raw.get("photos", [])
    if photos:
        result["photos"] = [
            {"url": p.get("url"), "title": p.get("title")} for p in photos
        ]

    # 去掉 None 值，减少输出体积
    return {k: v for k, v in result.items() if v is not None}


def _format_poi_detail(raw: dict) -> dict:
    """格式化 POI 详情（在 _format_poi 基础上补充深度信息）"""
    result = _format_poi(raw)
    result.update({
        "alias": raw.get("alias", ""),
        "website": raw.get("website", ""),
        "email": raw.get("email", ""),
        "business_area": raw.get("business_area", ""),
    })

    deep = raw.get("deep_info", {})
    if deep:
        result["deep_info"] = {
            "opening_hours": deep.get("opentime_info"),
            "parking": deep.get("park_type"),
            "avg_price": deep.get("avg_price"),
            "rating": deep.get("rating"),
        }
    return result


def _format_distance(meters: int) -> str:
    """1210 → '1.2公里'"""
    if meters >= 1000:
        return f"{meters / 1000:.1f}公里"
    return f"{meters}米"


def _format_duration(seconds: int) -> str:
    """3725 → '1小时2分'"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}小时{minutes}分"
    return f"{minutes}分钟"


# ═══════════════════════════════════════════════════════════════════════════════
# MCP Tools: POI 搜索
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def amap_text_search(
    keywords: str,
    city: str,
    citylimit: bool = True,
    types: str | None = None,
    offset: int = 20,
    page: int = 1,
    extensions: str = "all",
) -> dict:
    """
    按关键词在城市中搜索 POI（景点、餐厅、酒店、商场等）。

    适用场景:
    - 搜索目的地有哪些景点: keywords="景点", city="杭州"
    - 搜索特定美食: keywords="火锅", city="成都"
    - 搜索酒店: keywords="五星级酒店", city="上海", types="060000"

    Args:
        keywords: 搜索关键词，如 "故宫"、"美食"、"酒店"
        city: 中文城市名，如 "北京"、"上海"
        citylimit: 是否只返回指定城市的结果 (默认 True)
        types: POI 类型代码。常用代码:
            110000 = 风景名胜/景点
            050000 = 餐饮/美食
            060000 = 酒店/住宿
            100000 = 购物
            多个用 "|" 分隔: "110000|050000"
        offset: 每页条数 (默认 20, 最大 25)
        page: 页码 (默认 1)
        extensions: "base" 基本信息 / "all" 含照片和评分 (默认 all)

    Returns:
        dict: {
            "count": 总结果数,
            "pois": [{
                "id", "name", "address", "location": {"lng", "lat"},
                "province", "city", "district", "category", "tel",
                "distance", "rating", "cost", "photos": [{"url", "title"}]
            }, ...]
        }
    """
    logger.info("amap_text_search: keywords=%r, city=%r, types=%s", keywords, city, types)
    params: dict[str, Any] = {
        "keywords": keywords,
        "city": city,
        "citylimit": str(citylimit).lower(),
        "offset": offset,
        "page": page,
        "extensions": extensions,
    }
    if types:
        params["types"] = types

    data = _amap_get("/v3/place/text", **params)
    pois = data.get("pois", [])
    return {
        "count": data.get("count", "0"),
        "suggestion": data.get("suggestion", {}),
        "pois": [_format_poi(p) for p in pois],
    }


@mcp.tool()
def amap_around_search(
    longitude: float,
    latitude: float,
    keywords: str | None = None,
    types: str | None = None,
    radius: int = 3000,
    offset: int = 20,
    page: int = 1,
    extensions: str = "all",
) -> dict:
    """
    搜索某个坐标周边的 POI。

    适用场景:
    - 已知景点坐标，查找附近餐厅/酒店
    - 查找酒店周边的便利设施
    - 规划行程时评估某区域的生活配套

    Args:
        longitude: 中心点经度
        latitude: 中心点纬度
        keywords: 搜索关键词 (可选)
        types: POI 类型代码 (见 amap_text_search)
        radius: 搜索半径 (米), 默认 3000, 最大 50000
        offset: 每页条数
        page: 页码
        extensions: "base" / "all"

    Returns:
        dict: {"count": 总数, "pois": [...]}
    """
    logger.info("amap_around_search: lng=%f, lat=%f, radius=%d", longitude, latitude, radius)
    params: dict[str, Any] = {
        "location": f"{longitude},{latitude}",
        "radius": radius,
        "offset": offset,
        "page": page,
        "extensions": extensions,
    }
    if keywords:
        params["keywords"] = keywords
    if types:
        params["types"] = types

    data = _amap_get("/v3/place/around", **params)
    pois = data.get("pois", [])
    return {
        "count": data.get("count", "0"),
        "pois": [_format_poi(p) for p in pois],
    }


@mcp.tool()
def amap_poi_detail(
    poi_id: str,
    extensions: str = "all",
) -> dict:
    """
    根据高德 POI ID 查询详细信息。

    适用场景:
    - 从搜索结果中拿到 poi.id 后，深入查看电话、营业时间、评分、停车等

    Args:
        poi_id: 高德 POI ID (从 text_search / around_search 结果的 "id" 字段获取)
        extensions: "base" 基本信息 / "all" 含深度信息 (默认)

    Returns:
        dict: 包含 name, address, location, tel, website, deep_info 等完整信息
    """
    logger.info("amap_poi_detail: id=%s", poi_id)
    data = _amap_get("/v3/place/detail", id=poi_id, extensions=extensions)
    details = data.get("pois", [])
    if not details:
        return {"error": f"POI '{poi_id}' 未找到"}
    return _format_poi_detail(details[0])


# ═══════════════════════════════════════════════════════════════════════════════
# MCP Tools: 地理编码
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def amap_geocode(
    address: str,
    city: str | None = None,
) -> dict:
    """
    将结构化地址转换为经纬度坐标（正向地理编码）。

    适用场景:
    - 用户提到某个地址/地标，需要坐标来搜索周边或规划路线
    - 获取城市的 adcode（行政区划代码），用于后续天气查询

    Args:
        address: 中文地址，如 "北京市东城区天安门广场"、"杭州市西湖区灵隐寺"
        city: 可选城市名，缩小搜索范围提高精度

    Returns:
        dict: {
            "count": 匹配数量,
            "geocodes": [{
                "formatted_address": 标准地址,
                "location": {"lng": 116.397, "lat": 39.909},
                "adcode": "110101",
                "level": "门牌号/兴趣点/区县/城市"
            }, ...]
        }
    """
    logger.info("amap_geocode: address=%r, city=%s", address, city)
    params: dict[str, Any] = {"address": address}
    if city:
        params["city"] = city

    data = _amap_get("/v3/geocode/geo", **params)
    geocodes = data.get("geocodes", [])
    return {
        "count": data.get("count", "0"),
        "geocodes": [
            {
                "formatted_address": g.get("formatted_address"),
                "location": _parse_location(g.get("location", "0,0")),
                "adcode": g.get("adcode"),
                "level": g.get("level"),
            }
            for g in geocodes
        ],
    }


@mcp.tool()
def amap_reverse_geocode(
    longitude: float,
    latitude: float,
    extensions: str = "base",
    radius: int = 1000,
) -> dict:
    """
    将经纬度坐标转换为人类可读地址（逆向地理编码）。

    适用场景:
    - 有 GPS 坐标但不知道具体地址
    - 确认某个坐标点所在的城市/区县/街道

    Args:
        longitude: 经度
        latitude: 纬度
        extensions: "base" 仅地址 / "all" 还返回周边 POI 和道路
        radius: 周边 POI 搜索半径 (米), extensions="all" 时有效

    Returns:
        dict: {
            "formatted_address": "北京市东城区...",
            "address_component": {"province", "city", "district", "township", ...}
        }
    """
    logger.info("amap_reverse_geocode: lng=%f, lat=%f", longitude, latitude)
    data = _amap_get(
        "/v3/geocode/regeo",
        location=f"{longitude},{latitude}",
        extensions=extensions,
        radius=radius,
    )
    regeo = data.get("regeocode", {})
    result: dict[str, Any] = {
        "formatted_address": regeo.get("formatted_address"),
    }
    if "addressComponent" in regeo:
        result["address_component"] = regeo["addressComponent"]
    if extensions == "all":
        result["pois"] = regeo.get("pois", [])
        result["roads"] = regeo.get("roads", [])
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# MCP Tools: 天气 (组合工具: 行政区划 + 天气 API)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def amap_weather(
    city: str,
    extensions: str = "all",
) -> dict:
    """
    查询城市天气（当前 + 未来 4 天预报）。

    此工具内部自动将城市名转换为行政区划代码，你只需提供城市中文名即可。

    适用场景:
    - 旅行规划时评估天气对行程的影响
    - 根据温度给出穿衣建议
    - 雨天/高温时调整户外景点安排

    Args:
        city: 中文城市名，如 "北京"、"杭州市"、"成都"
        extensions: "base" 仅当前天气 / "all" 当前 + 4 天预报 (默认)

    Returns:
        dict: {
            "province": 省份,
            "city": 城市名,
            "adcode": 行政区划代码,
            "reporttime": 数据发布时间,
            "live": {"weather": "晴", "temperature": "26", "winddirection": "南",
                     "windpower": "≤3", "humidity": "45"},
            "forecasts": [
                {"date": "2026-07-21", "dayweather": "晴", "nightweather": "多云",
                 "daytemp": "33", "nighttemp": "24", "daywind": "南", "nightwind": "南",
                 "daypower": "≤3", "nightpower": "≤3"}, ...
            ]
        }
    """
    logger.info("amap_weather: city=%r, extensions=%s", city, extensions)

    # 第 1 步: 城市名 → adcode
    adcode = _get_adcode(city)

    # 第 2 步: adcode → 天气
    data = _amap_get("/v3/weather/weatherInfo", city=adcode, extensions=extensions)

    result: dict[str, Any] = {
        "province": data.get("province"),
        "city": data.get("city"),
        "adcode": data.get("adcode"),
        "reporttime": data.get("reporttime"),
    }

    # 实况天气
    if "lives" in data and data["lives"]:
        live = data["lives"][0]
        result["live"] = {
            "weather": live.get("weather"),
            "temperature": live.get("temperature"),
            "winddirection": live.get("winddirection"),
            "windpower": live.get("windpower"),
            "humidity": live.get("humidity"),
        }
    else:
        result["live"] = {}

    # 天气预报
    if "forecasts" in data and data["forecasts"]:
        result["forecasts"] = data["forecasts"][0].get("casts", [])
    else:
        result["forecasts"] = []

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# MCP Tools: 距离 & 路径规划
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.tool()
def amap_distance(
    origin_lng: float,
    origin_lat: float,
    dest_lng: float,
    dest_lat: float,
    type: int = 1,
) -> dict:
    """
    测量两点之间的距离和预计时间。

    适用场景:
    - 评估酒店到景点的通勤时间
    - 判断两个景点是否适合安排在同一天
    - 规划行程时估算交通耗时

    Args:
        origin_lng: 起点经度
        origin_lat: 起点纬度
        dest_lng: 终点经度
        dest_lat: 终点纬度
        type: 路径类型: 0=直线距离, 1=驾车 (默认), 3=步行

    Returns:
        dict: {
            "distance_meters": 1200,
            "duration_seconds": 300,
            "distance_text": "1.2公里",
            "duration_text": "5分钟"
        }
    """
    logger.info("amap_distance: (%.4f,%.4f) → (%.4f,%.4f) type=%d",
                origin_lng, origin_lat, dest_lng, dest_lat, type)
    data = _amap_get(
        "/v3/distance",
        origins=f"{origin_lng},{origin_lat}",
        destination=f"{dest_lng},{dest_lat}",
        type=str(type),
    )
    results = data.get("results", [])
    if not results:
        return {"error": "无法计算距离", "results": []}

    r = results[0]
    dist_m = int(r.get("distance", 0))
    dur_s = int(r.get("duration", 0))
    return {
        "origin_id": r.get("origin_id"),
        "dest_id": r.get("dest_id"),
        "distance_meters": dist_m,
        "duration_seconds": dur_s,
        "distance_text": _format_distance(dist_m),
        "duration_text": _format_duration(dur_s),
    }


@mcp.tool()
def amap_driving_route(
    origin_lng: float,
    origin_lat: float,
    dest_lng: float,
    dest_lat: float,
    strategy: int = 0,
) -> dict:
    """
    规划驾车路线，返回总距离、时间、过路费和分段指引。

    适用场景:
    - 城市间或远距离景点之间的驾车行程
    - 评估自驾游的耗时和过路费成本
    - 生成详细的路线说明

    Args:
        origin_lng, origin_lat: 起点坐标
        dest_lng, dest_lat: 终点坐标
        strategy: 路径策略:
            0 = 速度最快 (默认)
            1 = 避免收费
            2 = 距离最短
            3 = 避免高速
            4 = 躲避拥堵

    Returns:
        dict: {
            "distance_meters": 总距离,
            "duration_seconds": 总时间,
            "toll_fee_yuan": 过路费,
            "traffic_lights": 红绿灯数,
            "steps": [{"instruction", "road_name", "distance_meters", "duration_seconds", "orientation"}, ...]
        }
    """
    logger.info("amap_driving_route: (%.4f,%.4f) → (%.4f,%.4f) strategy=%d",
                origin_lng, origin_lat, dest_lng, dest_lat, strategy)
    data = _amap_get(
        "/v3/direction/driving",
        origin=f"{origin_lng},{origin_lat}",
        destination=f"{dest_lng},{dest_lat}",
        strategy=strategy,
        extensions="base",
    )
    route = data.get("route", {})
    paths = route.get("paths", [])
    if not paths:
        return {"error": "未找到驾车路线"}

    path = paths[0]
    return {
        "distance_meters": int(path.get("distance", 0)),
        "duration_seconds": int(path.get("duration", 0)),
        "toll_distance_meters": int(path.get("toll_distance", 0)),
        "toll_fee_yuan": float(path.get("tolls", 0)),
        "traffic_lights": int(path.get("traffic_lights", 0)),
        "steps": [
            {
                "instruction": s.get("instruction"),
                "road_name": s.get("road"),
                "distance_meters": int(s.get("distance", 0)),
                "duration_seconds": int(s.get("duration", 0)),
                "orientation": s.get("orientation"),
                "action": s.get("action"),
            }
            for s in path.get("steps", [])
        ],
    }


@mcp.tool()
def amap_walking_route(
    origin_lng: float,
    origin_lat: float,
    dest_lng: float,
    dest_lat: float,
) -> dict:
    """
    规划步行路线，返回距离、时间和步行指引。

    适用场景:
    - 相邻景点之间的步行导航
    - 判断酒店到附近餐厅/地铁站是否适合步行
    - 短距离（< 3km）出行建议

    注意: 高德步行 API 适用于 100km 以内的路线。

    Args:
        origin_lng, origin_lat: 起点坐标
        dest_lng, dest_lat: 终点坐标

    Returns:
        dict: {
            "distance_meters": 步行距离,
            "duration_seconds": 步行时间,
            "steps": [{"instruction", "road_name", "distance_meters", "duration_seconds",
                       "orientation", "action", "walk_type"}, ...]
        }
    """
    logger.info("amap_walking_route: (%.4f,%.4f) → (%.4f,%.4f)",
                origin_lng, origin_lat, dest_lng, dest_lat)
    data = _amap_get(
        "/v3/direction/walking",
        origin=f"{origin_lng},{origin_lat}",
        destination=f"{dest_lng},{dest_lat}",
    )
    route = data.get("route", {})
    paths = route.get("paths", [])
    if not paths:
        return {"error": "未找到步行路线"}

    path = paths[0]
    return {
        "distance_meters": int(path.get("distance", 0)),
        "duration_seconds": int(path.get("duration", 0)),
        "steps": [
            {
                "instruction": s.get("instruction"),
                "road_name": s.get("road"),
                "distance_meters": int(s.get("distance", 0)),
                "duration_seconds": int(s.get("duration", 0)),
                "orientation": s.get("orientation"),
                "action": s.get("action"),
                "walk_type": s.get("walk_type"),
            }
            for s in path.get("steps", [])
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logger.info("Amap MCP Server 启动中...")
    mcp.run(transport="stdio")
