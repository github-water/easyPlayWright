"""
示例：通过 api 层（对外接口）抓取 36kr 快讯列表
访问 https://www.36kr.com/newsflashes/catalog/0
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.newsflash_api import NewsflashApi
from pkg.logger import logger


def main():
    logger.info("=== 36kr 快讯抓取示例启动 ===")

    # 通过 api 层调用，屏蔽内部实现细节
    api = NewsflashApi(output_dir="output")

    # 方式一：专用接口
    data = api.fetch_36kr(scroll_times=3, export_fmt="json")

    # 方式二：通用抓取接口（可复用于其他页面）
    # data = api.scrape_page(
    #     url="https://www.36kr.com/newsflashes/catalog/0",
    #     item_selector=".newsflash-item",
    #     fields={
    #         "title":   {"selector": ".article-item-title", "attr": None},
    #         "link":    {"selector": "a.item-title",        "attr": "href"},
    #         "time":    {"selector": ".time",               "attr": None},
    #         "summary": {"selector": ".article-item-description", "attr": None},
    #     },
    #     scroll_times=3,
    #     export_filename="36kr_newsflash.json",
    # )

    logger.info("=== 数据预览（前5条）===")
    for i, item in enumerate(data[:5], 1):
        logger.info(
            f"[{i}] {item.get('title', 'N/A')} | "
            f"{item.get('time', 'N/A')} | "
            f"{item.get('link', 'N/A')}"
        )

    logger.info(f"=== 完成，共 {len(data)} 条，结果已保存至 output/ ===")


if __name__ == "__main__":
    main()
