"""
api 层 - HTTP 服务入口（微视视频提取）
职责：将微视视频 URL 提取功能封装为 HTTP 接口，供外部系统调用
C4 定位：System Interface（HTTP 协议版本）
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

from adapter.browser import BrowserAdapter
from adapter.page import PageAdapter
from adapter.weishi import WeishiAdapter
from pkg.logger import logger

video_router = APIRouter()


# ------------------------------------------------------------------ #
# 请求/响应模型
# ------------------------------------------------------------------ #

class VideoExtractRequest(BaseModel):
    """视频提取请求体"""
    url: str = Field(..., description="微视分享链接（必填）")
    timeout: float = Field(default=30.0, description="等待视频元素超时秒数")


class VideoExtractData(BaseModel):
    """视频提取响应数据"""
    video_url: str = Field(description="提取到的视频资源 URL")
    source_url: str = Field(description="原始分享链接")


class VideoExtractResponse(BaseModel):
    """视频提取响应体"""
    success: bool
    data:Optional[VideoExtractData] = None
    error: Optional[str] = None


# ------------------------------------------------------------------ #
# 路由
# ------------------------------------------------------------------ #

@video_router.post("/api/weiShi/extract", response_model=VideoExtractResponse)
async def extract_video(req: VideoExtractRequest):
    """
    微视视频 URL 提取接口。
    - 传入微视 App 分享链接，返回视频资源直链（mp4）。
    - 异步处理，不阻塞其他请求。
    """
    logger.info(f"[HTTP] 收到视频提取请求：url={req.url}")

    try:
        browser_adapter = await BrowserAdapter.get_instance()
        page_adapter = PageAdapter(browser_adapter.context)
        page = await page_adapter.new_page()

        try:
            weishi = WeishiAdapter(page)
            video_url = await weishi.get_video_url(req.url, timeout=req.timeout)
        finally:
            await page.close()

        if not video_url:
            logger.warning(f"[HTTP] 未能提取到视频 URL：{req.url}")
            return VideoExtractResponse(
                success=False,
                error="未能从页面提取到视频 URL，请确认链接有效或适当增大 timeout",
            )

        logger.info(f"[HTTP] 视频提取成功：{video_url[:80]}...")
        return VideoExtractResponse(
            success=True,
            data=VideoExtractData(
                video_url=video_url,
                source_url=req.url,
            ),
        )

    except Exception as e:
        logger.error(f"[HTTP] 视频提取失败：{e}", exc_info=True)
        return VideoExtractResponse(
            success=False,
            error=f"服务器内部错误：{str(e)}",
        )
