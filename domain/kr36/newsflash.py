"""
domain 层 - 业务域
职责：定义业务用例语义，编排 component 完成具体业务流程。
C4 定位：System Context（最高层，描述"做什么"而非"怎么做"）
"""
import time
from typing import List, Dict
from playwright.sync_api import Page

from component.scraper import ScraperComponent
from component.exporter import ExporterComponent
from pkg.logger import logger


# 36kr 快讯列表页 URL
NEWSFLASH_URL = "https://www.36kr.com/newsflashes/catalog/0"

# 列表项选择器
ITEM_SELECTOR = ".newsflash-item"

# 字段映射配置
FIELDS = {
    "title": {"selector": "a.item-title", "attr": None},
    "link": {"selector": "a.item-title", "attr": "href"},
    "time": {"selector": ".time", "attr": None},
    "summary": {"selector": ".item-desc span", "attr": None},
}

# 36kr 域名前缀（相对链接补全用）
BASE_URL = "https://www.36kr.com"


class NewsflashDomain:
    """
    36kr 快讯业务域。
    描述业务意图：打开快讯页 -> 滚动加载 -> 提取数据 -> 补全链接 -> 导出。
    不直接依赖 adapter，通过 component 层驱动外部交互。
    """

    def __init__(self, page: Page):
        self.page = page
        self.scraper = ScraperComponent()
        self.exporter = ExporterComponent(output_dir="output")

    def open(self, scroll_times: int = 3) -> "NewsflashDomain":
        """打开快讯页并滚动加载更多内容"""
        logger.info(f"[Domain] 打开 36kr 快讯页: {NEWSFLASH_URL}")
        self.page.goto(NEWSFLASH_URL, wait_until="domcontentloaded")
        self.page.wait_for_selector(ITEM_SELECTOR, state="visible", timeout=30000)
        logger.info("[Domain] 页面加载完成，开始滚动")

        for i in range(scroll_times):
            self.page.evaluate("window.scrollBy(0, 800)")
            time.sleep(1.2)
            logger.debug(f"[Domain] 滚动 {i + 1}/{scroll_times}")

        return self

    def fetch(self) -> List[Dict]:
        """提取快讯列表并补全链接"""
        logger.info("[Domain] 开始提取快讯数据")
        data = self.scraper.extract_list(self.page, ITEM_SELECTOR, FIELDS)

        for item in data:
            link = item.get("link")
            if link and link.startswith("/"):
                item["link"] = BASE_URL + link

        logger.info(f"[Domain] 共提取 {len(data)} 条快讯")
        return data

    def save(self, data:List[Dict], fmt: str = "json") -> str:
        """持久化数据"""
        if fmt == "csv":
            return self.exporter.to_csv(data, filename="36kr_newsflash.csv")
        return self.exporter.to_json(data, filename="36kr_newsflash.json")

    def run(self, scroll_times: int = 3, fmt: str = "json") -> List[Dict]:
        """业务用例入口：打开 -> 抓取 -> 保存"""
        self.open(scroll_times=scroll_times)
        data = self.fetch()
        self.save(data, fmt=fmt)
        return data
