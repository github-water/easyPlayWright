"""
adapter 层 - 外部系统适配器
职责：对接 Playwright Page 对象，封装页面级原子操作。
C4 定位：External System Adapter（Container 边界）
"""
import time
from playwright.sync_api import Page, BrowserContext

from pkg.config import config
from pkg.logger import logger


class PageAdapter:
    """Playwright 页面适配器：导航、等待、滚动"""

    def __init__(self, context: BrowserContext):
        self._context = context
        self._timeout = config.get("browser", "timeout", default=30000)

    def new_page(self) -> Page:
        """创建新页面"""
        page = self._context.new_page()
        page.set_default_timeout(self._timeout)
        return page

    def goto(self, page: Page, url: str, wait_until: str = "domcontentloaded") -> Page:
        """导航到指定 URL"""
        logger.info(f"[Adapter] 导航到: {url}")
        page.goto(url, wait_until=wait_until, timeout=self._timeout)
        return page

    def wait_for_selector(self, page: Page, selector: str, state: str = "visible") -> None:
        """等待元素出现"""
        logger.debug(f"[Adapter] 等待元素: {selector}, state={state}")
        page.wait_for_selector(selector, state=state, timeout=self._timeout)

    def scroll_to_bottom(self, page: Page, step: int = 500, delay: float = 0.3) -> None:
        """滚动到页面底部"""
        last_height = page.evaluate("document.body.scrollHeight")
        while True:
            page.evaluate(f"window.scrollBy(0, {step})")
            time.sleep(delay)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        logger.debug("[Adapter] 已滚动至页面底部")

    def scroll_by(self, page: Page, distance: int = 500) -> None:
        """向下滚动指定像素"""
        page.evaluate(f"window.scrollBy(0, {distance})")

    def close_page(self, page: Page) -> None:
        """关闭页面"""
        page.close()
        logger.debug("[Adapter] 页面已关闭")
