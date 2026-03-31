"""
api 层 - 对外暴露的系统接口层
职责：作为系统唯一入口，被外部调用者（测试/脚本/CI/其他系统）使用。
      内部委托 component 编排、adapter 对接 Playwright。
C4 定位：System Interface（Container 对外边界）
"""
from typing import List, Dict

from adapter.browser import BrowserAdapter
from adapter.page import PageAdapter
from component.scraper import ScraperComponent
from component.navigator import NavigatorComponent
from component.exporter import ExporterComponent
from pkg.logger import logger


class NewsflashApi:
    """
    快讯抓取系统对外接口。
    外部调用者只需依赖此类，无需感知内部 component/adapter 细节。
    """

    def __init__(self, output_dir: str = "output"):
        self._output_dir = output_dir

    def fetch_36kr(
        self,
        scroll_times: int = 3,
        export_fmt: str = "json",
    ) -> List[Dict]:
        """
        抓取 36kr 快讯列表。

        :param scroll_times: 页面滚动次数，越多加载越多条目
        :param export_fmt: 导出格式，'json' 或 'csv'，默认 json
        :return: 快讯数据列表，每条包含 title/link/time/summary
        """
        from domain.kr36.newsflash import NewsflashDomain

        logger.info(f"[API] fetch_36kr 调用，scroll_times={scroll_times}, fmt={export_fmt}")

        with BrowserAdapter() as context:
            page_adapter = PageAdapter(context)
            page = page_adapter.new_page()

            domain = NewsflashDomain(page)
            data = domain.run(scroll_times=scroll_times, fmt=export_fmt)

        logger.info(f"[API] fetch_36kr 完成，返回 {len(data)} 条数据")
        return data

    def scrape_page(
        self,
        url: str,
        item_selector: str,
        fields: Dict[str, Dict],
        scroll_times: int = 0,
        export_filename: str = "",
        export_fmt: str = "json",
    ) -> List[Dict]:
        """
        通用页面抓取接口。

        :param url: 目标页面 URL
        :param item_selector: 列表项 CSS 选择器
        :param fields: 字段配置字典
        :param scroll_times: 滚动次数
        :param export_filename: 导出文件名（含扩展名）
        :param export_fmt: 'json' 或 'csv'
        :return: 抓取结果列表
        """
        logger.info(f"[API] scrape_page 调用，url={url}")

        navigator = NavigatorComponent()
        scraper = ScraperComponent()
        exporter = ExporterComponent(output_dir=self._output_dir)

        with BrowserAdapter() as context:
            page_adapter = PageAdapter(context)
            page = page_adapter.new_page()
            navigator.open_url(page, url, wait_selector=item_selector)

            if scroll_times > 0:
                data = scraper.scroll_and_extract(
                    page, item_selector, fields, scroll_times=scroll_times
                )
            else:
                data = scraper.extract_list(page, item_selector, fields)

        if export_filename:
            if export_fmt == "csv":
                exporter.to_csv(data, filename=export_filename)
            else:
                exporter.to_json(data, filename=export_filename)

        logger.info(f"[API] scrape_page 完成，返回 {len(data)} 条数据")
        return data
