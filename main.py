"""
easyPlayWright 主入口
通过 api 层（对外接口）调用系统能力。
用法：python main.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.newsflash_api import NewsflashApi
from pkg.logger import logger


def main():
    logger.info("=== easyPlayWright 启动 ===")

    api = NewsflashApi(output_dir="output")
    data = api.fetch_36kr(scroll_times=3, export_fmt="json")

    logger.info(f"任务完成，共抓取 {len(data)} 条数据，结果保存至 output/")

    # 预览前 5 条
    for i, item in enumerate(data[:5], 1):
        logger.info(
            f"[{i}] {item.get('title', 'N/A')} | "
            f"{item.get('time', 'N/A')} | "
            f"{item.get('link', 'N/A')}"
        )


if __name__ == "__main__":
    main()
