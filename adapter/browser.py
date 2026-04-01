"""
adapter 层 - 外部系统适配器
职责：对接 Playwright 外部自动化系统，封装浏览器生命周期。
C4 定位：External System Adapter（Container 边界）

支持两种使用模式：
1. 一次性模式（async with 语句）：每次创建/销毁，适用于脚本和示例
2. 单例模式（get_instance）：单浏览器多 Context 架构，适用于 HTTP 服务
   - Playwright + Browser 全局唯一（只启动一次浏览器进程）
   - 按 storage_state 缓存不同 BrowserContext（Cookie 隔离）
   - 按 page_key 缓存已打开的 Page（避免重复导航）
   - 异步架构，支持多请求并发（不同 Page 可同时操作）

注意：Playwright 异步 API 要求所有操作在同一事件循环中执行。
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Playwright, Page

from pkg.config import config
from pkg.logger import logger


class BrowserAdapter:
    """Playwright 异步浏览器适配器：启动、创建上下文、关闭"""

    # 全局单例：共享的 Playwright 和 Browser 实例
    _playwright: Playwright = None
    _browser: Browser = None

    # Context 缓存：key = storage_state 路径, value = BrowserAdapter 实例
    _instances: dict = {}
    _lock = asyncio.Lock()

    def __init__(self, storage_state: str = None):
        """
        :param storage_state: 登录态文件路径（优先级高于 config.yaml）。
                              传入后自动携带 Cookie，无需重复登录。
                              为 None 时读取 config.yaml 中 browser.storage_state。
        """
        self._context: BrowserContext = None
        self._storage_state = storage_state
        self._is_singleton = False
        # Page 缓存：key = page_key（如 "qwen"）, value = Page 实例
        self._pages: dict = {}
        # Page 锁：key = page_key, value = asyncio.Lock（保证同一 Page 串行操作）
        self._page_locks: dict = {}
        # 一次性模式专用（不共享全局浏览器）
        self._own_playwright: Playwright = None
        self._own_browser: Browser = None

    # ------------------------------------------------------------------ #
    # 全局浏览器管理（单例模式共享）
    # ------------------------------------------------------------------ #

    @classmethod
    async def _ensure_browser(cls) -> Browser:
        """确保全局 Playwright + Browser 已启动，返回 Browser 实例"""
        if cls._browser is not None and cls._browser.is_connected():
            return cls._browser

        browser_type = config.get("browser", "type", default="chromium")
        channel = config.get("browser", "channel", default="")
        headless = config.get("browser", "headless", default=False)
        slow_mo = config.get("browser", "slow_mo", default=0)

        logger.info(f"[Adapter] 启动全局浏览器: {browser_type}, channel={channel or '内置'}, headless={headless}")

        cls._playwright = await async_playwright().start()
        browser_launcher = getattr(cls._playwright, browser_type)

        launch_kwargs = dict(
            headless=headless,
            slow_mo=slow_mo,
            args=cls._get_stealth_args(),
        )
        if channel:
            launch_kwargs["channel"] = channel

        cls._browser = await browser_launcher.launch(**launch_kwargs)
        return cls._browser

    @staticmethod
    def _get_stealth_args() -> list:
        """获取反自动化检测的浏览器启动参数"""
        return [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-popup-blocking",
            "--disable-background-networking",
            "--disable-dev-shm-usage",
            "--start-maximized",
        ]

    @classmethod
    async def _create_context(cls, storage_state: str = None) -> BrowserContext:
        """在全局 Browser 上创建新的 BrowserContext（含反检测措施）"""
        state = storage_state or config.get("browser", "storage_state", default="")
        if state and Path(state).exists():
            logger.info(f"[Adapter] 加载登录态: {state}")
        else:
            if state:
                logger.warning(f"[Adapter] 登录态文件不存在，将以未登录状态启动: {state}")
            state = None

        context_kwargs = dict(
            no_viewport=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        if state:
            context_kwargs["storage_state"] = state

        context = await cls._browser.new_context(**context_kwargs)
        # 注入反自动化检测脚本（在每个新页面加载前执行）
        await context.add_init_script(cls._get_stealth_script())
        return context

    @staticmethod
    def _get_stealth_script() -> str:
        """返回反自动化检测的 JS 注入脚本"""
        return """
            // 隐藏 webdriver 标志
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // 伪造 chrome 对象
            if (!window.chrome) {
                window.chrome = {
                    runtime: {
                        onMessage: { addListener: function() {} },
                        sendMessage: function() {}
                    },
                    loadTimes: function() { return {}; },
                    csi: function() { return {}; },
                };
            }

            // 伪造 plugins（真实浏览器通常有插件）
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' },
                ]
            });

            // 伪造 languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en-US', 'en']
            });

            // 隐藏 Headless 特征
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });

            // 伪造 permissions API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // 隐藏自动化相关的 window 属性
            delete window.__playwright;
            delete window.__pw_manual;
        """

    # ------------------------------------------------------------------ #
    # 单例模式：单浏览器多 Context
    # ------------------------------------------------------------------ #

    @classmethod
    async def get_instance(cls, storage_state: str = None) -> "BrowserAdapter":
        """
        获取单例实例（按 storage_state 缓存 Context）。
        所有实例共享同一个浏览器进程，不同 storage_state 使用独立 Context（Cookie 隔离）。
        """
        cache_key = storage_state or "__default__"
        async with cls._lock:
            instance = cls._instances.get(cache_key)
            if instance is not None and instance._is_context_alive():
                logger.debug(f"[Adapter] 复用 Context: {cache_key}")
                return instance

            await cls._ensure_browser()

            logger.info(f"[Adapter] 创建新 Context: {cache_key}")
            instance = cls(storage_state=storage_state)
            instance._is_singleton = True
            instance._context = await cls._create_context(storage_state)
            cls._instances[cache_key] = instance
            return instance

    def _is_context_alive(self) -> bool:
        """检查 Context 是否仍然存活"""
        try:
            if self._context is None:
                return False
            if BrowserAdapter._browser is None or not BrowserAdapter._browser.is_connected():
                return False
            return True
        except Exception:
            return False

    @classmethod
    async def close_all(cls):
        """关闭所有缓存 Page、Context 和全局浏览器（用于应用退出时清理）"""
        async with cls._lock:
            for key, instance in list(cls._instances.items()):
                for page_key in list(instance._pages.keys()):
                    try:
                        page = instance._pages.pop(page_key, None)
                        if page and not page.is_closed():
                            await page.close()
                    except Exception:
                        pass
                logger.info(f"[Adapter] 关闭 Context: {key}")
                try:
                    if instance._context:
                        await instance._context.close()
                except Exception:
                    pass
                instance._context = None
            cls._instances.clear()

            if cls._browser:
                try:
                    await cls._browser.close()
                except Exception:
                    pass
                cls._browser = None
            if cls._playwright:
                try:
                    await cls._playwright.stop()
                except Exception:
                    pass
                cls._playwright = None
            logger.info("[Adapter] 全局浏览器已关闭")

    # ------------------------------------------------------------------ #
    # 核心属性与方法
    # ------------------------------------------------------------------ #

    async def launch(self) -> BrowserContext:
        """
        启动浏览器并返回 BrowserContext。
        仅用于一次性模式（async with 语句），创建独立的 Playwright + Browser。
        """
        browser_type = config.get("browser", "type", default="chromium")
        headless = config.get("browser", "headless", default=False)
        slow_mo = config.get("browser", "slow_mo", default=0)
        viewport = config.get("browser", "viewport", default={"width": 1920, "height": 1080})

        storage_state = self._storage_state or config.get("browser", "storage_state", default="")
        if storage_state and Path(storage_state).exists():
            logger.info(f"[Adapter] 加载登录态: {storage_state}")
        else:
            if storage_state:
                logger.warning(f"[Adapter] 登录态文件不存在，将以未登录状态启动: {storage_state}")
            storage_state = None

        channel = config.get("browser", "channel", default="")

        logger.info(f"[Adapter] 启动浏览器（一次性模式）: {browser_type}, channel={channel or '内置'}, headless={headless}")

        self._own_playwright = await async_playwright().start()
        browser_launcher = getattr(self._own_playwright, browser_type)

        launch_kwargs = dict(
            headless=headless,
            slow_mo=slow_mo,
            args=self._get_stealth_args(),
        )
        if channel:
            launch_kwargs["channel"] = channel

        self._own_browser = await browser_launcher.launch(**launch_kwargs)

        context_kwargs = dict(
            no_viewport=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )
        if storage_state:
            context_kwargs["storage_state"] = storage_state

        self._context = await self._own_browser.new_context(**context_kwargs)
        # 注入反自动化检测脚本
        await self._context.add_init_script(self._get_stealth_script())
        return self._context

    @property
    def context(self) -> BrowserContext:
        """获取当前 BrowserContext"""
        return self._context

    # ------------------------------------------------------------------ #
    # Page 缓存（单例模式下复用已打开的页面）
    # ------------------------------------------------------------------ #

    async def get_or_create_page(self, page_key: str) -> Page:
        """
        获取或创建缓存的 Page（仅单例模式生效）。
        同一 page_key 复用已打开的页面，避免重复导航和页面创建。
        """
        cached_page = self._pages.get(page_key)
        if cached_page is not None and not cached_page.is_closed():
            logger.debug(f"[Adapter] 复用缓存 Page: {page_key}")
            return cached_page

        logger.info(f"[Adapter] 创建新 Page: {page_key}")
        timeout = config.get("browser", "timeout", default=30000)
        page = await self._context.new_page()
        page.set_default_timeout(timeout)
        self._pages[page_key] = page
        # 为新 Page 创建对应的锁
        self._page_locks[page_key] = asyncio.Lock()
        return page

    def has_cached_page(self, page_key: str) -> bool:
        """检查指定 key 的 Page 是否已缓存且存活"""
        cached = self._pages.get(page_key)
        return cached is not None and not cached.is_closed()

    def get_page_lock(self, page_key: str) -> asyncio.Lock:
        """
        获取指定 Page 的异步锁。
        同一 page_key 的操作通过此锁串行执行，不同 page_key 之间可并发。
        """
        if page_key not in self._page_locks:
            self._page_locks[page_key] = asyncio.Lock()
        return self._page_locks[page_key]

    async def close_page(self, page_key: str) -> None:
        """关闭并移除指定 key 的缓存 Page 和对应的锁"""
        cached = self._pages.pop(page_key, None)
        self._page_locks.pop(page_key, None)
        if cached and not cached.is_closed():
            try:
                await cached.close()
            except Exception:
                pass
            logger.info(f"[Adapter] 缓存 Page 已关闭: {page_key}")

    async def close(self):
        """
        关闭资源。
        单例模式下此方法为空操作（由 close_all 统一管理），
        非单例模式下关闭独立的浏览器实例。
        """
        if self._is_singleton:
            logger.debug("[Adapter] 单例模式，跳过关闭")
            return
        await self._close_disposable()

    async def _close_disposable(self):
        """关闭一次性模式的独立资源"""
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
        if self._own_browser:
            try:
                await self._own_browser.close()
            except Exception:
                pass
        if self._own_playwright:
            try:
                await self._own_playwright.stop()
            except Exception:
                pass
        self._context = None
        self._own_browser = None
        self._own_playwright = None
        logger.info("[Adapter] 浏览器已关闭（一次性模式）")

    # ------------------------------------------------------------------ #
    # async with 语句支持（一次性模式，向后兼容）
    # ------------------------------------------------------------------ #

    async def __aenter__(self) -> BrowserContext:
        return await self.launch()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
