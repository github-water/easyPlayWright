"""
adapter 层 - 微视页面适配器
职责：对接微视 App 分享链接页面，提取视频资源 URL。
C4 定位：External System Adapter（对接微视外部系统）
"""
import asyncio

from playwright.async_api import Page

from pkg.logger import logger

# 视频元素选择器
VIDEO_SELECTOR = "video#vpjs-video_html5_api"


class WeishiAdapter:
    """
    微视页面适配器（异步版）。
    通过 Playwright 打开微视分享链接，等待 video 元素加载后提取 src。
    """

    def __init__(self, page: Page):
        self.page = page

    async def get_video_url(self, share_url: str, timeout: float = 30.0) -> str:
        """
        打开微视分享链接，提取 video 元素的 src 属性。

        :param share_url: 微视分享页面 URL
        :param timeout: 等待 video 元素超时秒数
        :return: 视频资源 URL（如 //v.weishi.qq.com/...mp4?...），空字符串表示未找到
        """
        timeout_ms = int(timeout * 1000)
        logger.info(f"[Adapter][Weishi] 打开页面: {share_url}")
        await self.page.goto(share_url, wait_until="domcontentloaded")

        # 等待 video 元素出现
        logger.debug(f"[Adapter][Weishi] 等待 video 元素...")
        try:
            await self.page.wait_for_selector(VIDEO_SELECTOR, state="attached", timeout=timeout_ms)
        except Exception:
            logger.warning("[Adapter][Weishi] video 元素未找到，尝试直接读取")

        # 等待 src 属性被填充（src 可能由 JS 动态赋值）
        src = ""
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            src = await self.page.eval_on_selector(
                VIDEO_SELECTOR,
                "el => el.getAttribute('src') || el.src || ''",
            )
            if src:
                break
            await asyncio.sleep(0.5)

        if src:
            # 补全协议头
            if src.startswith("//"):
                src = "https:" + src
            logger.info(f"[Adapter][Weishi] 提取到视频 URL: {src[:80]}...")
        else:
            logger.warning("[Adapter][Weishi] 未能提取到视频 src")

        return src
