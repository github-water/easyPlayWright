"""
adapter 层 - 外部系统适配器
职责：对接 Playwright 外部自动化系统，封装浏览器生命周期。
C4 定位：External System Adapter（Container 边界）
"""
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Playwright

from pkg.config import config
from pkg.logger import logger


class BrowserAdapter:
    """Playwright 浏览器适配器：启动、创建上下文、关闭"""

    def __init__(self, storage_state: str = None):
        """
        :param storage_state: 登录态文件路径（优先级高于 config.yaml）。
                              传入后自动携带 Cookie，无需重复登录。
                              为 None 时读取 config.yaml 中 browser.storage_state。
        """
        self._playwright: Playwright = None
        self._browser: Browser = None
        self._context: BrowserContext = None
        self._storage_state = storage_state

    def launch(self) -> BrowserContext:
        """启动浏览器并返回 BrowserContext"""
        browser_type = config.get("browser", "type", default="chromium")
        headless = config.get("browser", "headless", default=False)
        slow_mo = config.get("browser", "slow_mo", default=0)
        viewport = config.get("browser", "viewport", default={"width": 1920, "height": 1080})

        # 登录态：优先使用构造函数传入的值，其次读取 config.yaml
        storage_state = self._storage_state or config.get("browser", "storage_state", default="")
        if storage_state and Path(storage_state).exists():
            logger.info(f"[Adapter] 加载登录态: {storage_state}")
        else:
            if storage_state:
                logger.warning(f"[Adapter] 登录态文件不存在，将以未登录状态启动: {storage_state}")
            storage_state = None

        logger.info(f"[Adapter] 启动浏览器: {browser_type}, headless={headless}")

        self._playwright = sync_playwright().start()
        browser_launcher = getattr(self._playwright, browser_type)
        self._browser = browser_launcher.launch(headless=headless, slow_mo=slow_mo)

        context_kwargs = dict(
            viewport={"width": viewport["width"], "height": viewport["height"]},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        if storage_state:
            context_kwargs["storage_state"] = storage_state

        self._context = self._browser.new_context(**context_kwargs)
        return self._context

    def close(self):
        """关闭浏览器及 Playwright 实例"""
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        logger.info("[Adapter] 浏览器已关闭")

    def __enter__(self) -> BrowserContext:
        return self.launch()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
