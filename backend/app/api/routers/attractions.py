"""
景点图片路由

GET /api/attractions/{name}/images → 根据景点名称搜索 Unsplash 高清图片
"""

# ═══════════════════════════════════════════════════════════════════════
# FastAPI 知识点:
#   路径参数 (Path Parameter):
#     {name} 写在 URL 路径中，是必填的。FastAPI 自动将其绑定到同名的函数参数。
#     如: GET /api/attractions/西湖/images → name = "西湖"
#
#   查询参数 (Query Parameter):
#     ?max_images=3 写在 URL 问号后面，是可选的。有默认值即为可选。
#     Query(ge=1, le=30) 限定取值范围 1-30。
# ═══════════════════════════════════════════════════════════════════════

import httpx
import logging
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import UnsplashSearchResult
from app.services.unsplash_service import search_attraction_images, UnsplashAPIError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{name}/images", response_model=UnsplashSearchResult)
async def get_attraction_images(
    name: str,
    max_images: int = Query(
        default=5,
        ge=1,
        le=30,
        description="最大返回图片数（1-30，默认 5）",
    ),
):
    """
    根据景点名称搜索 Unsplash 高质量旅游图片。

    路径参数 name 支持中文（URL 会自动编码为 UTF-8）。
    如: GET /api/attractions/西湖/images?max_images=3

    返回各尺寸图片 URL（raw/full/regular/small/thumb）及摄影师信息。
    """
    try:
        result = await search_attraction_images(name, max_images=max_images)
        return result

    except UnsplashAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504, detail="Unsplash API 请求超时，请稍后重试"
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=502, detail="无法连接 Unsplash API，请检查网络连接"
        )
    except Exception as e:
        logger.exception("景点图片搜索异常: name=%r", name)
        raise HTTPException(
            status_code=500, detail=f"图片搜索失败：{str(e)}"
        )
