"""
component 层 - 系统内部编排组件
职责：系统主动调用外部（adapter），组合原子操作完成数据抓取。
C4 定位：Component（系统边界内，驱动 adapter 与外部交互）
"""
import time
from typing import List, Dict, Optional
from playwright.sync_api import Page

from adapter.element import ElementAdapter
from pkg.logger import logger


class ScraperComponent:
    """抓取组件：编排元素操作，提取结构化数据"""

    def __init__(self):
        self.element = ElementAdapter()

    def extract_list(
        self,
        page: Page,
        item_selector: str,
        fields: Dict[str, Dict],
    ) -> List[Dict]:
        """
        通用列表抓取。
        :param page: Playwright Page 对象
        :param item_selector: 每个列表项的 CSS 选择器
        :param fields: 字段配置，格式：
            {
                "title": {"selector": ".title", "attr": None},     # attr=None 取 inner_text
                "link":  {"selector": "a",      "attr": "href"},   # 取属性值
            }
        :return: 结构化数据列表
        """
        items = page.locator(item_selector)
        count = items.count()
        logger.info(f"[Component] 共找到 {count} 个列表项")

        results = []
        for i in range(count):
            item = items.nth(i)
            record: Dict[str, Optional[str]] = {}
            for field_name, field_cfg in fields.items():
                selector = field_cfg.get("selector", "")
                attr = field_cfg.get("attr")
                try:
                    el = item.locator(selector)
                    if el.count() == 0:
                        record[field_name] = None
                    elif attr:
                        record[field_name] = el.first.get_attribute(attr)
                    else:
                        record[field_name] = el.first.inner_text().strip()
                except Exception as e:
                    logger.warning(f"[Component] 字段 [{field_name}] 提取失败: {e}")
                    record[field_name] = None
            results.append(record)

        return results

    def scroll_and_extract(
        self,
        page: Page,
        item_selector: str,
        fields: Dict[str, Dict],
        scroll_times: int = 3,
        scroll_step: int = 800,
        delay: float = 1.0,
    ) -> List[Dict]:
        """滚动加载后抓取列表数据"""
        for i in range(scroll_times):
            page.evaluate(f"window.scrollBy(0, {scroll_step})")
            time.sleep(delay)
            logger.debug(f"[Component] 第 {i + 1}/{scroll_times} 次滚动完成")

        return self.extract_list(page, item_selector, fields)
