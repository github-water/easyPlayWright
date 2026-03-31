"""
adapter 层 - 外部系统适配器
职责：对接 Playwright Locator，封装元素级原子操作。
C4 定位：External System Adapter（Container 边界）
"""
from typing import List, Optional
from playwright.sync_api import Page, Locator

from pkg.logger import logger


class ElementAdapter:
    """Playwright 元素适配器：查找、点击、输入、提取"""

    def find(self, page: Page, selector: str) -> Locator:
        """返回元素定位器"""
        return page.locator(selector)

    def find_all(self, page: Page, selector: str) -> List[Locator]:
        """返回所有匹配元素的定位器列表"""
        locator = page.locator(selector)
        count = locator.count()
        return [locator.nth(i) for i in range(count)]

    def click(self, page: Page, selector: str) -> None:
        """点击元素"""
        logger.debug(f"[Adapter] 点击元素: {selector}")
        page.locator(selector).click()

    def fill(self, page: Page, selector: str, value: str) -> None:
        """填写输入框"""
        logger.debug(f"[Adapter] 填写输入框: {selector} = {value}")
        page.locator(selector).fill(value)

    def get_text(self, page: Page, selector: str) -> str:
        """获取元素文本内容"""
        return page.locator(selector).inner_text()

    def get_all_texts(self, page: Page, selector: str) -> List[str]:
        """获取所有匹配元素的文本列表"""
        return page.locator(selector).all_inner_texts()

    def get_attribute(self, page: Page, selector: str, attr: str) -> Optional[str]:
        """获取元素属性值"""
        return page.locator(selector).get_attribute(attr)

    def get_all_attributes(self, page: Page, selector: str, attr: str) -> List[Optional[str]]:
        """获取所有匹配元素的指定属性值列表"""
        locator = page.locator(selector)
        count = locator.count()
        return [locator.nth(i).get_attribute(attr) for i in range(count)]

    def is_visible(self, page: Page, selector: str) -> bool:
        """判断元素是否可见"""
        return page.locator(selector).is_visible()

    def count(self, page: Page, selector: str) -> int:
        """统计匹配元素数量"""
        return page.locator(selector).count()
