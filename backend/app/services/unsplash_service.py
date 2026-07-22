"""
Unsplash 图片服务 — 根据景点名称搜索高质量旅游图片

使用 Unsplash API 的 GET /search/photos 端点，支持中文景点名称搜索。
搜索结果可作为 Attraction.image_url 的候选图片来源。

运行方式 (独立测试):
    python backend/app/services/unsplash_service.py
"""

# ═══════════════════════════════════════════════════════════════════════
# 1. 导入
# ═══════════════════════════════════════════════════════════════════════

import logging

import httpx

from app.config import UNSPLASH_API_KEY
from app.models.schemas import UnsplashImage, UnsplashImageUrls, UnsplashSearchResult

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# 2. 配置常量
# ═══════════════════════════════════════════════════════════════════════

UNSPLASH_BASE_URL = "https://api.unsplash.com"
UNSPLASH_HTTP_TIMEOUT = 15.0  # 秒
UNSPLASH_DEFAULT_PER_PAGE = 5
UNSPLASH_MAX_PER_PAGE = 30

# ═══════════════════════════════════════════════════════════════════════
# 3. 自定义异常
# ═══════════════════════════════════════════════════════════════════════


class UnsplashAPIError(Exception):
    """Unsplash API 返回错误时抛出。"""

    def __init__(self, status_code: int, message: str, path: str):
        self.status_code = status_code
        self.message = message
        self.path = path

        # 根据状态码生成友好的中文提示
        hints = {
            401: "API Key 无效或未配置，请检查 .env 中的 UNSPLASH_API_KEY",
            403: "请求被拒绝，可能是 API Key 权限不足或已达速率限制 (50次/小时)",
            404: "请求的资源不存在",
            500: "Unsplash 服务器内部错误，请稍后重试",
            503: "Unsplash 服务暂时不可用",
        }
        hint = hints.get(status_code, "")

        super().__init__(
            f"Unsplash API 错误 [{status_code}] {path}: {message}" + (f" ({hint})" if hint else "")
        )


# ═══════════════════════════════════════════════════════════════════════
# 4. 内部辅助函数
# ═══════════════════════════════════════════════════════════════════════


async def _unsplash_get(path: str, **params) -> dict:
    """
    发送 GET 请求到 Unsplash API（异步）。

    自动注入 Authorization 头、检查 HTTP 状态码。
    所有对外函数通过此入口调用 Unsplash API。

    Args:
        path: API 路径，如 "/search/photos"
        **params: 查询参数

    Returns:
        dict: API 返回的 JSON 数据

    Raises:
        UnsplashAPIError: API Key 未配置或 API 返回错误
        httpx.TimeoutException: 请求超时
    """
    if not UNSPLASH_API_KEY:
        raise UnsplashAPIError(401, "未配置 UNSPLASH_API_KEY，请在 .env 中设置", path)

    headers = {
        "Authorization": f"Client-ID {UNSPLASH_API_KEY}",
        "Accept-Version": "v1",
    }

    async with httpx.AsyncClient(timeout=UNSPLASH_HTTP_TIMEOUT) as client:
        resp = await client.get(
            f"{UNSPLASH_BASE_URL}{path}",
            params=params,
            headers=headers,
        )

        # 将 httpx 的 HTTP 错误转换为我们自定义的异常
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            error_detail = "未知错误"
            try:
                error_body = exc.response.json()
                errors = error_body.get("errors", [])
                error_detail = errors[0] if errors else str(error_body)
            except Exception:
                error_detail = exc.response.text or "未知错误"
            raise UnsplashAPIError(
                status_code=exc.response.status_code,
                message=error_detail,
                path=path,
            ) from exc

        return resp.json()


def _parse_image(raw: dict) -> UnsplashImage:
    """
    将 Unsplash API 原始图片数据解析为 UnsplashImage 模型。

    裁剪原始字段，只保留项目需要的核心信息。

    Args:
        raw: Unsplash API 返回的单张图片原始字典

    Returns:
        UnsplashImage: 解析后的图片模型
    """
    urls = raw.get("urls", {})
    user = raw.get("user", {})

    return UnsplashImage(
        image_id=raw.get("id", ""),
        description=raw.get("description"),
        alt_description=raw.get("alt_description"),
        width=raw.get("width", 0),
        height=raw.get("height", 0),
        urls=UnsplashImageUrls(
            raw=urls.get("raw", ""),
            full=urls.get("full", ""),
            regular=urls.get("regular", ""),
            small=urls.get("small", ""),
            thumb=urls.get("thumb", ""),
        ),
        photographer_name=user.get("name", "未知摄影师"),
        photographer_url=user.get("links", {}).get("html", ""),
    )


# ═══════════════════════════════════════════════════════════════════════
# 5. 主要公共函数
# ═══════════════════════════════════════════════════════════════════════


async def search_attraction_images(
    name: str,
    max_images: int = UNSPLASH_DEFAULT_PER_PAGE,
) -> UnsplashSearchResult:
    """
    根据景点名称搜索 Unsplash 图片。

    Args:
        name: 景点名称（支持中文），如 "西湖"、"故宫"、"The Great Wall"
        max_images: 最大返回图片数（1-30，默认 5）

    Returns:
        UnsplashSearchResult: 包含图片列表和总数信息。
                              has_results=False 表示该景点暂无图片。

    Raises:
        UnsplashAPIError: API 调用失败（含状态码和错误提示）
        httpx.TimeoutException: 请求超时
        httpx.ConnectError: 网络无法连接
    """
    per_page = max(1, min(max_images, UNSPLASH_MAX_PER_PAGE))

    logger.info("搜索景点图片: name=%r, max_images=%d", name, per_page)

    # 调用 Unsplash API
    data = await _unsplash_get(
        "/search/photos",
        query=name,
        per_page=per_page,
        orientation="landscape",
    )

    # 解析结果
    total = data.get("total", 0)
    raw_results = data.get("results", [])

    images = [_parse_image(item) for item in raw_results]

    result = UnsplashSearchResult(
        query=name,
        total=total,
        images=images,
        has_results=len(images) > 0,
    )

    # 无结果时给出反馈
    if not result.has_results:
        logger.info("景点 %r 暂无图片", name)
        print(f"此景点暂无图片: {name}")

    return result


# ═══════════════════════════════════════════════════════════════════════
# 6. 便捷函数
# ═══════════════════════════════════════════════════════════════════════


async def get_first_attraction_image(name: str) -> str | None:
    """
    获取景点的第一张 Unsplash 图片 URL（regular 尺寸）。

    便利封装，适用于只需要一张图片填充 Attraction.image_url 的场景。

    Args:
        name: 景点名称

    Returns:
        str | None: 图片 URL，无结果时返回 None
    """
    result = await search_attraction_images(name, max_images=1)
    if result.images:
        return result.images[0].urls.regular
    return None


# ═══════════════════════════════════════════════════════════════════════
# 7. 独立测试入口
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    import sys

    # Windows 终端默认 GBK 编码，强制输出 UTF-8 避免 UnicodeEncodeError
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    async def _test():
        """独立测试: 搜索几个景点图片"""
        test_attractions = [
            "西湖",
            "故宫",
            "上海外滩",
            "一个完全不存在的景点xyz123",
        ]

        for name in test_attractions:
            print(f"\n{'─' * 50}")
            print(f"搜索: {name}")
            try:
                result = await search_attraction_images(name, max_images=3)
                if result.has_results:
                    for i, img in enumerate(result.images, 1):
                        print(f"  [{i}] ID: {img.image_id}")
                        print(f"      描述: {img.description or img.alt_description or '(无)'}")
                        print(f"      摄影师: {img.photographer_name}")
                        print(f"      图片URL: {img.urls.regular}")
                        print(f"      尺寸: {img.width}x{img.height}")
                else:
                    print(f"  → 此景点暂无图片")
                print(f"  → 总计: {result.total} 个结果, 返回: {len(result.images)} 张")
            except UnsplashAPIError as e:
                print(f"  ✗ API 错误: {e}")
            except httpx.TimeoutException:
                print(f"  ✗ 请求超时，请检查网络连接")
            except httpx.ConnectError:
                print(f"  ✗ 无法连接 Unsplash API，请检查网络")
            except Exception as e:
                print(f"  ✗ 未知错误: {type(e).__name__}: {e}")

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(message)s",
    )

    asyncio.run(_test())
