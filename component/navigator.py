"""
component 层 - 系统内部编排组件
职责：系统主动调用外部（adapter），组合页面导航动作。
C4 定位：Component（系统边界内，驱动 adapter 与外部交互）
"""
from playwright.sync_api import Page

from adapter.page import PageAdapter
from pkg.logger import logger
from pkg.utils import take_screenshot


class NavigatorComponent:
    """导航组件：编排页面跳转、等待、截图等组合动作"""

    def open_url(
        self,
        page: Page,
        url: str,
        wait_selector: str = None,
        screenshot: bool = False,
    ) -> Page:
        """
        打开 URL，可选等待指定元素出现，可选截图。
        :param page: Playwright Page 对象
        :param url: 目标 URL
        :param wait_selector: 等待该 CSS 选择器可见后再返回
        :param screenshot: 是否截图
        """
        page.goto(url, wait_until="domcontentloaded")
        logger.info(f"[Component] 已导航到: {url}")

        if wait_selector:
            logger.info(f"[Component] 等待元素就绪: {wait_selector}")
            page.wait_for_selector(wait_selector, state="visible")

        if screenshot:
            path = take_screenshot(page, name="open_url")
            logger.info(f"[Component] 截图已保存: {path}")

        return page

    def reload(self, page: Page) -> None:
        """刷新当前页面"""
        logger.info("[Component] 刷新页面")
        page.reload(wait_until="domcontentloaded")

    def go_back(self, page: Page) -> None:
        """返回上一页"""
        logger.info("[Component] 返回上一页")
        page.go_back(wait_until="domcontentloaded")
